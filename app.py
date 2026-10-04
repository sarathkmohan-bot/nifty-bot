from flask import Flask
import os
import threading
import time
import yfinance as yf
from telegram import Bot
import asyncio

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

@app.route('/')
def home():
    return "Nifty Bot LIVE! 🚀"

def get_nifty():
    try:
        data = yf.Ticker("^NSEI").history(period="1d")
        return float(data['Close'].iloc[-1])
    except:
        return 25000

async def send_msg(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)

def bot_loop():
    while True:
        try:
            price = get_nifty()
            msg = f"📈 NIFTY: {price:.2f}\nSignal: WAIT - Bot is LIVE ✅"
            asyncio.run(send_msg(msg))
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(3600)  # 1 hour

# Start bot in background thread
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
