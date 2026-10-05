import os
from flask import Flask
import requests
import datetime, pytz
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64

app = Flask(__name__)

BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk","").strip()
CHAT_ID = os.environ.get("5444253276","").strip()

# paper trade
trade_state = {"position": None, "entry": 0, "pnl": 0, "capital": 100000}

def send_text(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
        return True
    except:
        return False

def send_chart(caption, df):
    try:
        plt.figure(figsize=(10,5))
        plt.plot(df.index, df['Close'], label='NIFTY')
        if 'EMA9' in df.columns:
            plt.plot(df.index, df['EMA9'], label='EMA9')
            plt.plot(df.index, df['EMA21'], label='EMA21')
        plt.legend(); plt.grid(alpha=0.3); plt.xticks(rotation=20)
        plt.title("NIFTY 15min EMA")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=130)
        buf.seek(0); plt.close()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', buf, 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        r = requests.post(url, files=files, data=data, timeout=20)
        print("Chart send:", r.text)
        return r.status_code == 200
    except Exception as e:
        print("Chart error:", e)
        return send_text(caption + f"\nChart error: {e}")

def get_nifty_live():
    try:
        s = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0','Referer':'https://www.nseindia.com/'}
        s.get("https://www.nseindia.com", headers=headers, timeout=8)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=8)
        for d in r.json()['data']:
            if d['index'] == 'NIFTY 50':
                return d['last']
    except: pass
    return "Closed"

def get_df():
    try:
        df = yf.download("^NSEI", period="5d", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        df.dropna(inplace=True)
        return df.tail(100)
    except Exception as e:
        print("yfinance error", e)
        return None

@app.route('/')
def home():
    ist = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%b %I:%M %p')
    live = get_nifty_live()
    df = get_df()
    if df is None:
        return f"Bot LIVE ✅<br>NIFTY: {live}<br>{ist}<br><a href='/telegram'>Test Chart</a> | <a href='/debug'>Debug</a>"
    price = round(float(df['Close'].iloc[-1]),2)
    # chart for web
    plt.figure(figsize=(8,4))
    plt.plot(df.index, df['Close']); plt.plot(df.index, df['EMA9']); plt.plot(df.index, df['EMA21'])
    buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
    b64 = base64.b64encode(buf.read()).decode()
    return f"Bot LIVE ✅<br>NIFTY Live: {live} | 15m: {price}<br>{ist}<br><img src='data:image/png;base64,{b64}' style='width:100%;max-width:700px'><br><br><a href='/telegram'>Test Chart</a> | <a href='/debug'>Debug</a>"

@app.route('/debug')
def debug():
    return f"BOT len={len(BOT_TOKEN)} CHAT={CHAT_ID[:4]}***"

@app.route('/telegram')
def test_tg():
    live = get_nifty_live()
    df = get_df()
    if df is None:
        send_text(f"✅ Bot working - NIFTY: {live} - but 15m data empty (market closed?)")
        return "Sent text - df None, market closed?"
    
    price = round(float(df['Close'].iloc[-1]),2)
    # signal
    if df['EMA9'].iloc[-2] <= df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]:
        sig = "BUY 🔼"
    elif df['EMA9'].iloc[-2] >= df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1]:
        sig = "SELL 🔽"
    else:
        sig = "HOLD"

    caption = f"📊 NIFTY 15min\nLive: {live} | 15m: {price}\nSignal: {sig}\nTime: {datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M %p')}"
    ok = send_chart(caption, df)
    return f"Chart sent={ok} - check Telegram"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
