import time, os, requests, yfinance as yf
import numpy as np
from flask import Flask
import threading, datetime
import pytz

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
    # Method 1 - Yahoo with full params (MOST STABLE ON RENDER)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        # This exact URL works on Render
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d&region=IN"
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Yahoo status {r.status_code}")
        if r.status_code == 200:
            j = r.json()
            meta = j['chart']['result'][0]['meta']
            price = meta.get('regularMarketPrice') or meta.get('previousClose') or meta.get('chartPreviousClose')
            if price:
                print(f"Yahoo price {price}")
                return float(price)
    except Exception as e:
        print(f"direct api fail {e}")

    # Method 2 - yfinance
    try:
        ticker = yf.Ticker("^NSEI")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            price = float(data['Close'].iloc[-1])
            print(f"yf price {price}")
            return price
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
        else:
            print("Price None - will retry")
        time.sleep(60)

@app.route('/')
def home():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist).strftime('%H:%M:%S %d-%b')
    # If last_price still 0, show loading
    if last_price == 0:
        status = f"Bot LIVE - Loading price... (History {len(history)}) Time: {now_ist} IST - Check logs for 'Yahoo status'"
    else:
        status = f"Bot LIVE - Price: {last_price:.2f} PnL: {total_pnl} Time: {now_ist} IST History: {len(history)}"
    return status

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
