import time, requests, numpy as np
from flask import Flask
#from tensorflow.keras.models import load_model # ninte model undel
# ninte existing imports same vekku

app = Flask(__name__)

# --- CONFIG ---
BOT_TOKEN = "8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk"
CHAT_ID = "5444253276"
SYMBOL = "^NSEI" # Nifty
history = [] # last 60 closes
in_position = False
entry_price = 0
total_pnl = 0

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_nifty():
    # ninte existing NSE function same
    try:
        #... your NSE fetch logic...
        return current_price
    except:
        return None

@app.route('/')
def home():
    return "Bot6 LIVE - EMA Filter"

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
            time.sleep(900)
            continue

        # --- LSTM PREDICTION (ninte model) ---
        # x = np.array(history).reshape...
        # predicted = model.predict(x)[0][0]
        predicted = price + np.random.randn()*10 # TEST - ninte model prediction ivide

        diff = predicted - price # CLIP OZHIVAKKI - full diff vekku

        # --- NEW EMA FILTER - ithaan main fix ---
        ema20 = np.mean(history[-20:]) # last 20 average = EMA simple
        is_uptrend = price > ema20 + 5
        is_downtrend = price < ema20 - 5

        # --- PAPER TRADING LOGIC ---
        if is_uptrend and diff > 5 and not in_position:
            entry_price = price
            in_position = True
            send_telegram(f"🟢 PAPER BUY\nNIFTY: {price:.2f} (+{price-ema20:.2f} above EMA)\nEMA20: {ema20:.2f}\nPred Diff: {diff:.2f}\nEntry: {entry_price:.2f}")

        elif is_downtrend and diff < -5 and in_position:
            pnl = price - entry_price
            total_pnl += pnl
            in_position = False
            send_telegram(f"🔴 PAPER SELL\nNIFTY: {price:.2f}\nTrade PnL: {pnl:.2f}\nTotal PnL: {total_pnl:.2f}")

        else:
            trend = "BULLISH" if is_uptrend else "BEARISH" if is_downtrend else "SIDEWAYS"
            status = "IN POSITION" if in_position else "NO POSITION"
            send_telegram(f"⏳ WAIT - {trend} - {status}\nNIFTY: {price:.2f} EMA20: {ema20:.2f} Diff: {diff:.2f}\nTotal PnL: {total_pnl:.2f}")

        time.sleep(900) # 15 min

# Start loop in background
import threading
threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    send_telegram("✅ nifty-bot-6 STARTED - Paper Money + EMA Filter + Real Nifty ₹1L Virtual")
    app.run(host="0.0.0.0", port=10000)
