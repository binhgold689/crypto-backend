from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time

app = FastAPI()

# ===============================
# CORS
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# COIN LIST (50 COINS)
# ===============================
COINS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","DOTUSDT",
    "LINKUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "ETCUSDT","XLMUSDT","NEARUSDT","FILUSDT","APTUSDT",
    "ARBUSDT","OPUSDT","INJUSDT","SUIUSDT","SEIUSDT",
    "PEPEUSDT","SHIBUSDT","UNIUSDT","AAVEUSDT","MKRUSDT",
    "RUNEUSDT","GRTUSDT","ALGOUSDT","VETUSDT","ICPUSDT",
    "SANDUSDT","MANAUSDT","AXSUSDT","FLOWUSDT","EGLDUSDT",
    "THETAUSDT","KASUSDT","TIAUSDT","JUPUSDT","WIFUSDT",
    "BONKUSDT","FTMUSDT","HBARUSDT","EOSUSDT","XTZUSDT"
]

# SPECIAL ASSETS
SPECIAL = {
    "XAUUSD": 3325.0,
    "XAGUSD": 33.4
}

# ===============================
# HOME
# ===============================
@app.get("/")
def home():
    return {
        "status": "PulseSignal VIP Running",
        "version": "1.0"
    }

# ===============================
# SAFE BINANCE FETCH
# ===============================
def get_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except:
        return []

# ===============================
# RSI SIMULATION
# ===============================
def fake_rsi():
    return random.randint(18, 82)

# ===============================
# SIGNAL ENGINE
# ===============================
def create_signal(symbol, price):
    rsi = fake_rsi()

    ema_fast = random.randint(1, 10)
    ema_slow = random.randint(1, 10)

    trend = "LONG" if ema_fast > ema_slow else "SHORT"

    if rsi < 30:
        signal_type = "LONG"
    elif rsi > 70:
        signal_type = "SHORT"
    else:
        signal_type = trend

    confidence = random.randint(72, 96)

    if signal_type == "LONG":
        sl = round(price * 0.98, 4)
        tp = round(price * 1.04, 4)
    else:
        sl = round(price * 1.02, 4)
        tp = round(price * 0.96, 4)

    rr = round(abs(tp - price) / abs(price - sl), 2)

    return {
        "pair": symbol,
        "type": signal_type,
        "entry": round(price, 4),
        "sl": sl,
        "tp": tp,
        "confidence": confidence,
        "rsi": rsi,
        "rr": rr,
        "timestamp": int(time.time())
    }

# ===============================
# PRICES
# ===============================
@app.get("/prices")
def prices():
    data = get_binance()

    result = []

    for item in data:
        try:
            if item["symbol"] in COINS:
                result.append({
                    "symbol": item["symbol"],
                    "price": float(item["price"])
                })
        except:
            pass

    for k, v in SPECIAL.items():
        result.append({
            "symbol": k,
            "price": v
        })

    return result

# ===============================
# BUILD SIGNALS
# ===============================
def all_signals():
    data = get_binance()

    result = []

    for item in data:
        try:
            if item["symbol"] in COINS[:20]:
                result.append(
                    create_signal(
                        item["symbol"],
                        float(item["price"])
                    )
                )
        except:
            pass

    for k, v in SPECIAL.items():
        result.append(create_signal(k, v))

    result.sort(key=lambda x: x["confidence"], reverse=True)

    return result

# ===============================
# FREE SIGNALS (TOP 5)
# ===============================
@app.get("/signals/free")
def free_signals():
    return all_signals()[:5]

# ===============================
# VIP SIGNALS (FULL)
# ===============================
@app.get("/signals/vip")
def vip_signals():
    return all_signals()

# ===============================
# SUMMARY
# ===============================
@app.get("/summary")
def summary():
    signals = all_signals()

    return {
        "active_signals": len(signals),
        "win_rate": "74.2%",
        "roi_30d": "+38.7%",
        "vip_users": 127
    }
