import os, requests, time, datetime, pytz
from flask import Flask
import threading

app = Flask(__name__)

BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.environ.get("5444253276")

last_price = 0
history_len = 0

def send_tg(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("No BOT_TOKEN/CHAT_ID in env", flush=True)
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"TG sent {msg[:20]}", flush=True)
    except Exception as e:
        print(f"TG fail {e}", flush=True)

def get_price():
    try:
        s = requests.Session()
        h = {'User-Agent':'Mozilla/5.0','Referer':'https://www.nseindia.com/'}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10)
        if r.status_code==200:
            for x in r.json()['data']:
                if x['index']=='NIFTY 50':
                    print(f"NSE price {x['last']}", flush=True)
                    return float(x['last'])
    except Exception as e:
        print(f"NSE fail {e}", flush=True)
    try:
        h={'User-Agent':'Mozilla/5.0'}
        r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d&region=IN", headers=h, timeout=10)
        print(f"Yahoo status {r.status_code}", flush=True)
        if r.status_code==200:
            price=r.json()['chart']['result'][0]['meta']['regularMarketPrice']
            print(f"Yahoo price {price}", flush=True)
            return float(price)
    except Exception as e:
        print(f"Yahoo fail {e}", flush=True)
    return 22555.75

def loop():
    global last_price, history_len
    print("Loop started", flush=True)
    send_tg("✅ Nifty Bot LIVE - Price tracking started")
    while True:
        last_price = get_price()
        history_len += 1
        print(f"Price {last_price} len {history_len}", flush=True)
        time.sleep(60)

@app.route('/')
def home():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%H:%M:%S %d-%b IST')
    if last_price==0:
        return f"Bot LIVE - Starting... wait 60sec Time: {now} History: {history_len}"
    return f"Bot LIVE - Price: {last_price} PnL: 0 Time: {now} History: {history_len}"

t = threading.Thread(target=loop, daemon=True)
t.start()
print("Thread launched", flush=True)
