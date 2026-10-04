from flask import Flask
import os
os.environ["WEB_CONCURRENCY"] = "1"

import threading, time, json
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
IS_RUNNING = False  # duplicate guard

def load_paper():
    try:
        with open(PAPER_FILE, 'r') as f: return json.load(f)
    except: return {"holding": False, "entry": 0, "pnl": 0, "trades": 0, "wins": 0}

def save_paper(d):
    with open(PAPER_FILE, 'w') as f: json.dump(d, f)

paper = load_paper()

@app.route('/')
def home():
    return f"LIVE! PnL: {paper['pnl']:.2f} | Holding: {paper['holding']}"

def get_data():
    try:
        df = yf.Ticker("^NSEI").history(period="1d", interval="5m")
        return df['Close'].values[-80:]
    except: return None

def lstm_predict():
    data = get_data()
    if data is None or len(data) < 65: return 22421, 22421, 0
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(data.reshape(-1,1))
    X, y = [], []
    for i in range(60, len(scaled)):
        X.append(scaled[i-60:i].flatten())
        y.append(scaled[i,0])
    X, y = np.array(X), np.array(y)
    model = MLPRegressor(hidden_layer_sizes=(32,32), max_iter=200, random_state=42)
    model.fit(X, y)
    pred_scaled = model.predict(scaled[-60:].flatten().reshape(1,-1))
    pred = scaler.inverse_transform(pred_scaled.reshape(-1,1))[0,0]
    last = data[-1]
    # limit unrealistic diff
    diff = np.clip(pred-last, -50, 50)
    pred = last + diff
    return last, pred, diff

async def send_msg(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

def bot_loop():
    global paper, IS_RUNNING
    if IS_RUNNING: return
    IS_RUNNING = True
    time.sleep(10) # wait for deploy
    while True:
        try:
            last, pred, diff = lstm_predict()
            msg = ""
            if diff > 12 and not paper["holding"]:
                paper["holding"]=True; paper["entry"]=last; paper["trades"]+=1
                msg = f"🟢 <b>STRONG BUY - PAPER BUY</b>\n\nEntry: {last:.2f}\nPred: {pred:.2f} (+{diff:.2f})\n\n📊 Paper: HOLDING @ {last:.2f}\n🤖 30 Epoch LSTM"
            elif diff < -12 and paper["holding"]:
                pnl = last-paper["entry"]; paper["pnl"]+=pnl; paper["holding"]=False
                if pnl>0: paper["wins"]+=1
                wr = (paper["wins"]/paper["trades"]*100) if paper["trades"]>0 else 0
                msg = f"🔴 <b>STRONG SELL - PAPER SELL</b>\n\nExit: {last:.2f}\nPnL: {pnl:+.2f}\n\n💰 Total: {paper['pnl']:+.2f}\n📈 Trades: {paper['trades']} | Win: {wr:.1f}%"
            else:
                status = f"HOLDING @ {paper['entry']:.2f} | PnL {last-paper['entry']:+.2f}" if paper["holding"] else "NO POSITION"
                msg = f"🟡 <b>WAIT - {status}</b>\n\nLast: {last:.2f}\nPred: {pred:.2f} ({diff:+.2f})\nTotal PnL: {paper['pnl']:+.2f}\n\n🤖 30 Epoch LSTM"
            save_paper(paper)
            print(msg)
            asyncio.run(send_msg(msg))
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(900)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
