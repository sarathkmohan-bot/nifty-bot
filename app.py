from flask import Flask
import os, time, requests, threading
from telegram import Bot
import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

@app.route('/')
def home(): return "OK"

async def send(text):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
    except Exception as e: print(e)

def get_nifty():
    try:
        s = requests.Session()
        h = {"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10).json()
        for i in r['data']:
            if i['index']=='NIFTY 50':
                return float(i['last']), float(i['previousClose']), float(i['variation']), float(i['percentChange'])
    except Exception as e:
        print(f"fail {e}")
    return None

def loop():
    time.sleep(5)
    asyncio.run(send("✅ <b>BOT FIXED - SINGLE MESSAGE</b>"))
    while True:
        try:
            d = get_nifty()
            if d:
                last, prev, chg, pct = d
                ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
                msg = f"🟢 <b>NIFTY LIVE: {last:.2f} ({chg:+.2f} {pct:+.2f}%)</b>\nPrev: {prev:.2f}\nTime: {ist.strftime('%I:%M %p IST')}\nBot: nifty-bot-5 ✅"
                asyncio.run(send(msg))
        except Exception as e:
            print(e)
        time.sleep(900)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
