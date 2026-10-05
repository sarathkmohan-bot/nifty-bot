from flask import Flask
import os, time, requests, threading, json, datetime
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from telegram import Bot
import asyncio
import yfinance as yf

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PAPER_FILE = "/tmp/paper.json"

def load_paper():
    try:
        with open(PAPER_FILE,'r') as f: return json.load(f)
    except:
        return {"holding":False,"entry":0,"pnl":0,"trades":0,"wins":0}

def save_paper(d):
    with open(PAPER_FILE,'w') as f: json.dump(d,f)

paper = load_paper()

@app.route('/')
def home():
    return f"Bot6 LIVE | PnL: {paper['pnl']:.2f} | Trades: {paper['trades']} | Holding: {paper['holding']}"

def get_live():
    try:
        s = requests.Session()
        h = {"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10).json()
        for i in r['data']:
            if i['index']=='NIFTY 50':
                return float(i['last']), float(i['previousClose']), float(i['variation']), float(i['percentChange'])
    except Exception as e:
        print(f"NSE fail {e}")
    return None

def get_hist(live):
    try:
        df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
        closes = df['Close'].values.flatten()
        closes[-1] = live
        return closes
    except:
        return np.array([live]*80)

async def send(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

def loop():
    global paper
    time.sleep(5)
    asyncio.run(send("✅ <b>nifty-bot-6 STARTED</b>\nPaper Money + Real Nifty\n₹1L Virtual Balance"))

    while True:
        try:
            data = get_live()
            if not data:
                time.sleep(60); continue
            last, prev, chg, pct = data
            closes = get_hist(last)

            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(closes.reshape(-1,1))
            X,y=[],[]
            for i in range(60,len(scaled)):
                X.append(scaled[i-60:i].flatten())
                y.append(scaled[i,0])
            X,y=np.array(X),np.array(y)
            model=MLPRegressor(hidden_layer_sizes=(64,32), max_iter=200, random_state=42)
            model.fit(X,y)
            pred_s=model.predict(scaled[-60:].flatten().reshape(1,-1))
            pred=float(scaler.inverse_transform(pred_s.reshape(-1,1))[0,0])
            diff=float(np.clip(pred-last, -80, 80))
            pred=last+diff
            ist=(datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%I:%M %p IST")

            if diff>15 and not paper["holding"]:
                paper["holding"]=True
                paper["entry"]=last
                paper["trades"]+=1
                save_paper(paper)
                msg=f"🟢 <b>PAPER BUY</b>\n\n<b>NIFTY: {last:.2f} ({chg:+.2f} {pct:+.2f}%)</b>\nEntry: {last:.2f}\nPred: {pred:.2f} ({diff:+.2f})\n\n💰 Paper: HOLDING 1 Lot\n⏰ {ist}"
                asyncio.run(send(msg))

            elif diff<-15 and paper["holding"]:
                pnl=last-paper["entry"]
                paper["pnl"]+=pnl
                paper["holding"]=False
                if pnl>0: paper["wins"]+=1
                wr=(paper["wins"]/paper["trades"]*100) if paper["trades"] else 0
                save_paper(paper)
                msg=f"🔴 <b>PAPER SELL</b>\n\n<b>NIFTY: {last:.2f} ({chg:+.2f} {pct:+.2f}%)</b>\nExit: {last:.2f}\nTrade: {pnl:+.2f}\nTotal PnL: {paper['pnl']:+.2f}\nWinRate: {wr:.0f}% ({paper['wins']}/{paper['trades']})\n\n⏰ {ist}"
                asyncio.run(send(msg))

            else:
                if paper["holding"]:
                    upnl=last-paper["entry"]
                    msg=f"🟡 <b>HOLDING</b> Paper PnL: {upnl:+.2f}\n<b>NIFTY: {last:.2f} ({chg:+.2f} {pct:+.2f}%)</b>\nPred: {pred:.2f} ({diff:+.2f})\nTotal: {paper['pnl']:+.2f}\n{ist}"
                else:
                    msg=f"⚪ <b>WAIT</b>\n<b>NIFTY: {last:.2f} ({chg:+.2f} {pct:+.2f}%)</b>\nPred: {pred:.2f} ({diff:+.2f})\nTotal PnL: {paper['pnl']:+.2f}\n{ist}"
                print(msg)
                asyncio.run(send(msg))

        except Exception as e:
            print(f"Err {e}")
        time.sleep(900)

if not hasattr(app,'started'):
    app.started=True
    threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
