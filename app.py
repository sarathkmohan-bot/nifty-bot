import os
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask
import requests
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.getenv("5444253276")

balance = 100000
qty = 0
pnl = 0
last_buy_price = 0

def get_nifty_data():
    data = yf.download("^NSEI", period="5d", interval="15m", progress=False, auto_adjust=False)
    # FIX for new yfinance - flatten columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.dropna(inplace=True)
    data['EMA9'] = data['Close'].ewm(span=9).mean()
    data['EMA21'] = data['Close'].ewm(span=21).mean()
    return data

def get_signal(data):
    last = data.iloc[-1]
    prev = data.iloc[-2]
    if prev['EMA9'] < prev['EMA21'] and last['EMA9'] > last['EMA21']:
        return "BUY"
    elif prev['EMA9'] > prev['EMA21'] and last['EMA9'] < last['EMA21']:
        return "SELL"
    else:
        return "HOLD"

def send_telegram_chart(data, signal, price):
    global balance, qty, pnl, last_buy_price
    
    msg_extra = ""
    price_val = float(price)
    if signal == "BUY" and qty == 0:
        qty = 1
        last_buy_price = price_val
        balance -= price_val
        msg_extra = f"\nAUTO BUY @ {price_val:.1f}"
    elif signal == "SELL" and qty > 0:
        pnl = price_val - last_buy_price
        balance += price_val
        qty = 0
        msg_extra = f"\nAUTO SELL @ {price_val:.1f} | P&L: {pnl:.1f}"

    plt.figure(figsize=(8,5))
    plt.plot(data['Close'].tail(50), label='NIFTY', color='blue')
    plt.plot(data['EMA9'].tail(50), label='EMA9', color='orange')
    plt.plot(data['EMA21'].tail(50), label='EMA21', color='green')
    plt.title(f"NIFTY 15m - {signal} - {price_val:.1f}")
    plt.legend()
    plt.grid(True)
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    caption = f"NIFTY 15m\nLive: {price_val:.1f}\nSignal: {signal}\nTime: {datetime.now().strftime('%I:%M %p')}\nPaper: Rs.{balance:.0f}\nQty: {qty} | P&L: Rs.{pnl:.0f}{msg_extra}"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': buf}
    data_tg = {'chat_id': CHAT_ID, 'caption': caption}
    r = requests.post(url, files=files, data=data_tg)
    return r.text

@app.route("/")
def home():
    try:
        df = get_nifty_data()
        # FIX: .item() use cheythu value edukkum
        price = float(df['Close'].iloc[-1])
        signal = get_signal(df)
        return f"NIFTY 15m<br>Live: {price:.1f}<br>Signal: {signal}<br>Time: {datetime.now().strftime('%I:%M %p')}<br><br><a href='/telegram'>Send Telegram</a>"
    except Exception as e:
        return f"Error: {e}"

@app.route("/telegram")
def telegram_route():
    try:
        df = get_nifty_data()
        price = float(df['Close'].iloc[-1])
        signal = get_signal(df)
        result = send_telegram_chart(df, signal, price)
        return f"Telegram Sent! {signal} @ {price} <br>{result}"
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
