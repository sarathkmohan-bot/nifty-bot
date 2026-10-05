import os, requests, datetime, pytz
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.environ.get("5444253276")

def get_price():
    # Try NSE
    try:
        s = requests.Session()
        h = {'User-Agent':'Mozilla/5.0','Referer':'https://www.nseindia.com/'}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10)
        if r.status_code==200:
            for x in r.json()['data']:
                if x['index']=='NIFTY 50':
                    return float(x['last']), "NSE"
    except: pass
    # Try Yahoo
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d&region=IN", headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
        if r.status_code==200:
            price = r.json()['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price), "Yahoo"
    except: pass
    return 24850.0, "Fallback"

@app.route('/')
def home():
    price, source = get_price()
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%H:%M:%S %d-%b %Y IST')
    return f"Bot LIVE - Price: {price} ({source}) Time: {now}"

@app.route('/telegram')
def test_tg():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": "✅ Test from Render - Bot working"}, timeout=10)
        return f"Telegram status: {r.text}"
    except Exception as e:
        return f"TG fail {e}"
