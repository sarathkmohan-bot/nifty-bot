import time, os, requests, yfinance as yf
import numpy as np
from flask import Flask
import threading, datetime

app = Flask(__name__)
BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.environ.get("5444253276")
SYMBOL = "^NSEI"
history = []
total_pnl = 0
last_price = 0
in_position = False
entry_price = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_nifty():
    try:
        ticker = yf.Ticker(SYMBOL)
        # Try intraday first
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        # Fallback daily for weekend
        data = ticker.history(period="5d", interval="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"yfinance err {e}")
    return None

def trading_loop():
    global history, total_pnl, last_price, in_position, entry_price
    send_telegram("✅ Bot LIVE on Render - Nifty Bot Started")
    while True:
        price = get_nifty()
        if price:
            last_price = price
            history.append(price)
            if len(history) > 60: history.pop(0)
            print(f"Price {price} len {len(history)}")
        time.sleep(60)

@app.route('/')
def home():
    status = f"Bot LIVE - Price: {last_price:.2f} PnL: {total_pnl} Time: {datetime.datetime.now().strftime('%H:%M:%S')} History: {len(history)}"
    return status

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
