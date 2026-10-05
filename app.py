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
    # Method 1: Direct Yahoo API (no crumb needed)
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            j = r.json()
            price = j['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except Exception as e:
        print(f"direct api fail {e}")

    # Method 2: Fallback yfinance
    try:
        ticker = yf.Ticker("^NSEI")
        data = ticker.history(period="5d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"yf fail {e}")
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
