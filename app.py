import time, os, requests, yfinance as yf
import numpy as np
from flask import Flask
import threading

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")  # Render env var ninnu edukkum
CHAT_ID = os.environ.get("CHAT_ID", "5444253276")
SYMBOL = "^NSEI"
history = []
in_position = False
entry_price = 0
total_pnl = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(e)

def get_nifty():
    try:
        ticker = yf.Ticker(SYMBOL)
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(e)
    return None

def trading_loop():
    global in_position, entry_price, total_pnl, history
    while True:
        price = get_nifty()
        if price is None:
            time.sleep(60)
            continue
        history.append(price)
        if len(history) > 60:
            history.pop(0)
        if len(history) < 60:
            print(f"Collecting {len(history)}/60")
            time.sleep(60)
            continue
        
        # EMA20 filter - NEW
        ema20 = float(np.mean(history[-20:]))
        is_uptrend = price > ema20 + 5
        is_downtrend = price < ema20 - 5
        
        # Simple momentum pred (replace with your LSTM if you have)
        diff = history[-1] - history[-5]  # 5 min momentum
        
        if is_uptrend and diff > 2 and not in_position:
            entry_price = price
            in_position = True
            send_telegram(f"🟢 PAPER BUY\nNIFTY: {price:.2f}\nEMA20: {ema20:.2f} (+{price-ema20:.1f})\nDiff: {diff:.2f}")

        elif is_downtrend and diff < -2 and in_position:
            pnl = price - entry_price
            total_pnl += pnl
            in_position = False
            send_telegram(f"🔴 PAPER SELL\nNIFTY: {price:.2f}\nTrade PnL: {pnl:.2f}\nTotal PnL: {total_pnl:.2f}")
        else:
            trend = "BULLISH" if is_uptrend else "BEARISH" if is_downtrend else "SIDEWAYS"
            print(f"WAIT {trend} {price:.2f} EMA {ema20:.2f} Diff {diff:.2f}")
        
        time.sleep(300) # 5 min for testing

@app.route('/')
def home():
    return f"Bot LIVE - Price: {history[-1] if history else 0} PnL: {total_pnl}"

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
