import os, time, pickle
from datetime import datetime
import pytz
import yfinance as yf
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

print("Loading model...")
model = load_model("nifty_30epoch.h5")
scaler = pickle.load(open("scaler.pkl", "rb"))

def send(msg):
try:
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
except Exception as e:
print(e)

print("24x7 Bot Started")
send("✅ Nifty Bot 24x7 LIVE aayi!")

while True:
try:
now = datetime.now(IST)
curr = now.hour60 + now.minute
if now.weekday()>=5 or curr < 960+15 or curr > 15*60+30:
print(f"{now} Market Closed")
time.sleep(1800)
continue

df = yf.download("^NSEI", period="5d", interval="15m", auto_adjust=True)
if isinstance(df.columns, pd.MultiIndex):
df.columns = df.columns.get_level_values(0)
df.columns = [c.lower() for c in df.columns]
close = df['close'].values.reshape(-1,1)
scaled = scaler.transform(close)
last_60 = scaled[-60:].reshape(1,60,1)
pred = scaler.inverse_transform(model.predict(last_60, verbose=0))
last = float(df['close'].iloc[-1])
pred_price = float(pred[0][0])
diff = pred_price - last

if abs(diff) > 10:
sig = "🟢 BUY" if diff>0 else "🔴 SELL"
msg = f"{sig} Nifty\nLast:{last:.2f} -> Pred:{pred_price:.2f} ({diff:+.2f})\nTime:{now.strftime('%I:%M %p')}"
send(msg)

time.sleep(900)
except Exception as e:
print(f"Error {e}")
time.sleep(60)