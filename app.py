from flask import Flask
import os
os.environ["WEB_CONCURRENCY"] = "1"
import threading, time, json, requests
import yfinance as yf
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from telegram import Bot
import asyncio

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PAPER_FILE = "/tmp/paper.json"
IS_RUNNING = False

def load_paper():
    try:
        import json as js
        with open(PAPER_FILE,'r') as f: return js.load(f)
    except: return {"holding":False,"entry":0,"pnl":0,"trades":0,"wins":0}
def save_paper(d):
    with open(PAPER_FILE,'w') as f: json.dump(d,f)
paper=load_paper()

@app.route('/')
def home(): return f"LIVE PnL {paper['pnl']}"

def get_live_nifty():
    try:
        # Method 1: yahoo 1m live
        df = yf.download("^NSEI", period="1d", interval="5m", progress=False, auto_adjust=True)
        if df is not None and len(df)>2:
            closes = df['Close'].values.flatten()
            last = float(closes[-1])
            prev = float(closes[-2]) if len(closes)>1 else last
            # for change vs yesterday close
            day_open = float(df['Open'].values[0])
            # prev close from 3mo daily
            daily = yf.download("^NSEI", period="5d", interval="1d", progress=False)
            prev_close = float(daily['Close'].values[-2]) if len(daily)>=2 else last
            change = last - prev_close
            pct = (change/prev_close*100) if prev_close else 0
            return last, prev_close, change, pct, closes
    except Exception as e:
        print("yahoo fail", e)
    # fallback to NSE api
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        r=requests.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=5)
        # Not reliable, just return None
    except: pass
    return None

def lstm_predict():
    data_res = get_live_nifty()
    if data_res is None: return None
    last, prev_close, change, pct, closes = data_res
    if len(closes) < 65:
        # not enough intraday, use daily for prediction
        df = yf.download("^NSEI", period="3mo", interval="1d", progress=False)['Close'].values.flatten()
        closes = df
    scaler=MinMaxScaler()
    scaled=scaler.fit_transform(closes.reshape(-1,1))
    if len(scaled)<65: return last, prev_close, change, pct, last, 0
    X,y=[],[]
    for i in range(60, len(scaled)):
        X.append(scaled[i-60:i].flatten())
        y.append(scaled[i,0])
    X,y=np.array(X),np.array(y)
    model=MLPRegressor(hidden_layer_sizes=(32,32), max_iter=200, random_state=42)
    model.fit(X,y)
    pred_s=model.predict(scaled[-60:].flatten().reshape(1,-1))
    pred=float(scaler.inverse_transform(pred_s.reshape(-1,1))[0,0])
    diff = np.clip(pred-last, -40, 40)
    pred = last + diff
    return last, prev_close, change, pct, pred, diff

async def send_msg(text):
    bot=Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

def bot_loop():
    global paper, IS_RUNNING
    if IS_RUNNING: return
    IS_RUNNING=True
    time.sleep(15)
    while True:
        try:
            res=lstm_predict()
            if res is None:
                time.sleep(60); continue
            last, prev_close, change, pct, pred, diff = res
            msg=""
            if diff>12 and not paper["holding"]:
                paper["holding"]=True; paper["entry"]=last; paper["trades"]+=1
                save_paper(paper)
                msg=f"🟢 <b>STRONG BUY</b>\n\n<b>NIFTY: {last:.2f} ({change:+.2f} {pct:+.2f}%)</b>\nEntry: {last:.2f}\nPred: {pred:.2f} ({diff:+.2f})\nPrevClose: {prev_close:.2f}\n\n📊 Paper HOLDING"
            elif diff<-12 and paper["holding"]:
                pnl=last-paper["entry"]; paper["pnl"]+=pnl; paper["holding"]=False
                if pnl>0: paper["wins"]+=1
                wr=(paper["wins"]/paper["trades"]*100) if paper["trades"] else 0
                save_paper(paper)
                msg=f"🔴 <b>STRONG SELL</b>\n\n<b>NIFTY: {last:.2f} ({change:+.2f} {pct:+.2f}%)</b>\nExit: {last:.2f}\nTrade: {pnl:+.2f}\nTotal PnL: {paper['pnl']:+.2f} | Win {wr:.0f}%"
            else:
                status=f"HOLDING {paper['entry']:.2f} PnL {last-paper['entry']:+.2f}" if paper["holding"] else "NO POSITION"
                save_paper(paper)
                msg=f"🟡 <b>{status}</b>\n\n<b>NIFTY: {last:.2f} ({change:+.2f} {pct:+.2f}%)</b>\nPred: {pred:.2f} ({diff:+.2f})\nPrev: {prev_close:.2f}\nTotal PnL: {paper['pnl']:+.2f}\n\n🤖 LSTM Live"
            print(msg)
            asyncio.run(send_msg(msg))
        except Exception as e:
            print(f"Err {e}")
        time.sleep(900)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
