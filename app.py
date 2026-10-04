from flask import Flask
import os, threading, time, json
import yfinance as yf
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from telegram import Bot
import asyncio
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# --- PAPER TRADING MEMORY ---
PAPER_FILE = "/tmp/paper.json"
def load_paper():
    try:
        with open(PAPER_FILE, 'r') as f: return json.load(f)
    except: return {"holding": False, "entry": 0, "pnl": 0, "trades": 0, "wins": 0}

def save_paper(data):
    with open(PAPER_FILE, 'w') as f: json.dump(data, f)

paper = load_paper()

@app.route('/')
def home():
    return f"Paper Trading LIVE! PnL: {paper['pnl']:.2f} | Holding: {paper['holding']}"

def get_data():
    try:
        df = yf.Ticker("^NSEI").history(period="5d", interval="15m")
        return df['Close'].values
    except: return None

def lstm_predict():
    data = get_data()
    if data is None or len(data) < 70: return 22421, 22421, 0
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(data.reshape(-1,1))
    X, y = [], []
    for i in range(60, len(scaled)):
        X.append(scaled[i-60:i].flatten())
        y.append(scaled[i])
    X, y = np.array(X), np.array(y).flatten()
    model = MLPRegressor(hidden_layer_sizes=(50,50), max_iter=300, random_state=42)
    model.fit(X, y)
    last_60 = scaled[-60:].flatten().reshape(1,-1)
    pred = scaler.inverse_transform(model.predict(last_60).reshape(-1,1))[0][0]
    return data[-1], pred, pred-data[-1]

async def send_msg(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

def bot_loop():
    global paper
    while True:
        try:
            last, pred, diff = lstm_predict()
            msg = ""
            # PAPER TRADING LOGIC
            if diff > 10 and not paper["holding"]:
                paper["holding"] = True
                paper["entry"] = last
                paper["trades"] += 1
                msg = f"🟢 <b>STRONG BUY - PAPER BUY EXECUTED</b>\n\nEntry: {last:.2f}\nPred: {pred:.2f} (+{diff:.2f})\n\n📊 Paper: HOLDING @ {last:.2f}"
            elif diff < -10 and paper["holding"]:
                pnl_trade = last - paper["entry"]
                paper["pnl"] += pnl_trade
                paper["holding"] = False
                if pnl_trade > 0: paper["wins"] += 1
                win_rate = (paper["wins"]/paper["trades"]*100) if paper["trades"]>0 else 0
                msg = f"🔴 <b>STRONG SELL - PAPER SELL EXECUTED</b>\n\nExit: {last:.2f}\nEntry: {paper['entry']:.2f}\nTrade PnL: {pnl_trade:+.2f}\n\n💰 Total PnL: {paper['pnl']:+.2f}\n📈 Trades: {paper['trades']} | Win: {win_rate:.1f}%"
            else:
                status = f"HOLDING @ {paper['entry']:.2f}" if paper["holding"] else "NO POSITION"
                pnl_now = (last - paper["entry"]) if paper["holding"] else 0
                msg = f"🟡 <b>WAIT - {status}</b>\n\nLast: {last:.2f}\nPred: {pred:.2f} ({diff:+.2f})\nLive PnL: {pnl_now:+.2f}\nTotal PnL: {paper['pnl']:+.2f}\n\n🤖 30 Epoch LSTM"

            save_paper(paper)
            print(msg)
            asyncio.run(send_msg(msg))
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(900) # 15 min

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
