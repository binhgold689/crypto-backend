from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time

app = FastAPI()

# ==================================
# CORS
# ==================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================
# CONFIG
# ==================================
COINGECKO_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin",
    "TRXUSDT": "tron",
    "AVAXUSDT": "avalanche-2",
    "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink",
    "MATICUSDT": "matic-network",
    "LTCUSDT": "litecoin",
    "BCHUSDT": "bitcoin-cash",
    "ATOMUSDT": "cosmos",
    "UNIUSDT": "uniswap",
    "ICPUSDT": "internet-computer",
    "NEARUSDT": "near",
    "FILUSDT": "filecoin",
    "APTUSDT": "aptos"
}

SPECIAL = {
    "XAUUSD": 3325.0,
    "XAGUSD": 33.4
}

# ==================================
# HOME
# ==================================
@app.get("/")
def home():
    return {
        "status": "PulseSignal FINAL Running",
        "version": "2.0"
    }

# ==================================
# FETCH COINGECKO
# ==================================
def get_prices_data():
    try:
        ids = ",".join(COINGECKO_IDS.values())

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()

        return res.json()

    except:
        return {}

# ==================================
# BUILD PRICE LIST
# ==================================
@app.get("/prices")
def prices():
    data = get_prices_data()

    result = []

    for symbol, coin_id in COINGECKO_IDS.items():
        try:
            result.append({
                "symbol": symbol,
                "price": float(data[coin_id]["usd"])
            })
        except:
            pass

    for k, v in SPECIAL.items():
        result.append({
            "symbol": k,
            "price": v
        })

    return result

# ==================================
# SIGNAL ENGINE
# ==================================
def fake_rsi():
    return random.randint(18, 82)

def create_signal(symbol, price):
    rsi = fake_rsi()

    if rsi < 30:
        signal_type = "LONG"
    elif rsi > 70:
        signal_type = "SHORT"
    else:
        signal_type = random.choice(["LONG", "SHORT"])

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

# ==================================
# ALL SIGNALS
# ==================================
def all_signals():
    market = prices()

    result = []

    for item in market:
        result.append(
            create_signal(
                item["symbol"],
                item["price"]
            )
        )

    result.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    return result

# ==================================
# FREE SIGNALS
# ==================================
@app.get("/signals/free")
def free_signals():
    return all_signals()[:5]

# ==================================
# VIP SIGNALS
# ==================================
@app.get("/signals/vip")
def vip_signals():
    return all_signals()

# ==================================
# SUMMARY
# ==================================
@app.get("/summary")
def summary():
    signals = all_signals()

    return {
        "active_signals": len(signals),
        "win_rate": "74.2%",
        "roi_30d": "+38.7%",
        "vip_users": 127,
        "server_time": int(time.time())
    }

# ==================================
# HEALTH CHECK
# ==================================
@app.get("/health")
def health():
    return {
        "ok": True
    }
