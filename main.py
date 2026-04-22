from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time

app = FastAPI()

# =====================================
# CORS
# =====================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================
# COINGECKO MAP (20 ASSETS)
# =====================================
COINS = {
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
    "LTCUSDT": "litecoin",
    "BCHUSDT": "bitcoin-cash",
    "ATOMUSDT": "cosmos",
    "UNIUSDT": "uniswap",
    "ICPUSDT": "internet-computer",
    "NEARUSDT": "near",
    "FILUSDT": "filecoin",
    "APTUSDT": "aptos",
    "MATICUSDT": "matic-network"
}

# SPECIAL MARKETS
SPECIAL = {
    "XAUUSD": 3325.0,
    "XAGUSD": 33.4
}

# =====================================
# HOME
# =====================================
@app.get("/")
def home():
    return {
        "status": "PulseSignal ULTIMATE Running",
        "version": "3.0",
        "time": int(time.time())
    }

# =====================================
# FETCH MARKET DATA
# =====================================
def fetch_market():
    try:
        ids = ",".join(COINS.values())

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()

        return res.json()

    except:
        return {}

# =====================================
# LIVE PRICES
# =====================================
@app.get("/prices")
def prices():
    data = fetch_market()

    result = []

    for symbol, coin_id in COINS.items():
        try:
            result.append({
                "symbol": symbol,
                "price": float(data[coin_id]["usd"])
            })
        except:
            pass

    for symbol, price in SPECIAL.items():
        result.append({
            "symbol": symbol,
            "price": price
        })

    return result

# =====================================
# RSI MOCK ENGINE
# =====================================
def fake_rsi():
    return random.randint(18, 82)

# =====================================
# SIGNAL ENGINE
# =====================================
def build_signal(symbol, price):
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

# =====================================
# ALL SIGNALS
# =====================================
def all_signals():
    market = prices()

    result = []

    for item in market:
        result.append(
            build_signal(
                item["symbol"],
                item["price"]
            )
        )

    result.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    return result

# =====================================
# FREE SIGNALS
# =====================================
@app.get("/signals/free")
def free_signals():
    return all_signals()[:5]

# =====================================
# VIP SIGNALS
# =====================================
@app.get("/signals/vip")
def vip_signals():
    return all_signals()

# =====================================
# SUMMARY
# =====================================
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

# =====================================
# FEAR GREED
# =====================================
@app.get("/fear-greed")
def fear_greed():
    score = random.randint(28, 81)

    if score < 40:
        label = "Fear"
    elif score > 70:
        label = "Greed"
    else:
        label = "Neutral"

    return {
        "score": score,
        "label": label
    }

# =====================================
# HEALTH CHECK
# =====================================
@app.get("/health")
def health():
    return {
        "ok": True
    }
