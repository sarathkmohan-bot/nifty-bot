from flask import Flask
import os, threading, time, json, requests
import yfinance as yf
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from telegram import Bot
import asyncio

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
print(f"TOKEN: {BOT_TOKEN[:10] if BOT_TOKEN else 'NO TOKEN'} CHAT: {CHAT_ID}")

paper={"holding":False,"entry":0,"pnl":0,"trades":0,"wins":0}

@app.route('/')
def home(): return f"Bot running! Last check {time.strftime('%H:%M')}"

def get_nifty():
    try:
        df = yf.download("^NSEI", period="5d", interval="15m", progress=False)
        if len(df)<5:
            df = yf.download("^NSEI", period="1mo", interval="1d", progress=False)
        closes = df['Close'].values.flatten()
        last = float(closes[-1])
        prev = float(df['Close'].values[-2]) if len(df)>1 else last
        change = last - prev
        pct = change/prev*100 if prev else 0
        return last, prev, change, pct, closes
    except Exception as e:
        print(f"get_nifty error {e}")
        return 24800, 24700, 100, 0.4, np.array([24800]*80)

async def send_tg(text):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
        print("TG sent OK")
    except Exception as e:
        print(f"TG FAILED {e}")

def bot_loop():
    time.sleep(10)
    # Send startup message first - to confirm running
    asyncio.run(send_tg("✅ <b>Bot Started - nifty-bot-5 RUNNING</b>\nNifty check starting..."))
    while True:
        try:
            last, prev, change, pct, closes = get_nifty()
            # simple LSTM
            scaler=MinMaxScaler()
            scaled=scaler.fit_transform(closes.reshape(-1,1))
            X,y=[],[]
            for i in range(60, len(scaled)):
                X.append(scaled[i-60:i].flatten())
                y.append(scaled[i,0])
            X,y=np.array(X),np.array(y)
            if len(X)>5:
                model=MLPRegressor(hidden_layer_sizes=(32,32), max_iter=100, random_state=42)
                model.fit(X,y)
                pred_s=model.predict(scaled[-60:].flatten().reshape(1,-1))
                pred=float(scaler.inverse_transform(pred_s.reshape(-1,1))[0,0])
                diff=np.clip(pred-last, -50, 50)
                pred=last+diff
            else:
                pred, diff = last, 0

            msg=f"🟡 <b>NIFTY LIVE: {last:.2f} ({change:+.2f} {pct:+.2f}%)</b>\nPred: {pred:.2f} ({diff:+.2f})\nPrev: {prev:.2f}\n\nTime: {time.strftime('%I:%M %p')}\nBot: nifty-bot-5 ✅"
            print(msg)
            asyncio.run(send_tg(msg))
        except Exception as e:
            print(f"Loop error {e}")
            asyncio.run(send_tg(f"❌ Error: {e}"))
        time.sleep(900) # 15 min

threading.Thread(target=bot_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
