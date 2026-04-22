from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COINS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","PAXGUSDT",
    "ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","DOTUSDT","LINKUSDT",
    "MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT","NEARUSDT","FILUSDT"
]

# Danh sách các cổng API dự phòng của Binance
BINANCE_ENDPOINTS = [
    "https://api1.binance.com/api/v3/ticker/price",
    "https://api2.binance.com/api/v3/ticker/price",
    "https://api3.binance.com/api/v3/ticker/price",
    "https://api.binance.com/api/v3/ticker/price"
]

def fetch_prices_safe():
    for url in BINANCE_ENDPOINTS:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Cổng {url} lỗi {response.status_code}, đang thử cổng khác...")
        except:
            continue
    return None

@app.get("/")
def home():
    return {"message": "PulseSignal VIP Online - Geo-Fix Enabled"}

@app.get("/prices")
def get_prices():
    data = fetch_prices_safe()
    
    if data is None:
        return {"error": "Tất cả các cổng Binance đều chặn IP của server. Hãy thử đổi khu vực (Region) trên Railway sang Europe."}
        
    result = []
    for item in data:
        symbol = item.get("symbol")
        if symbol in COINS:
            display_name = "XAUUSD" if symbol == "PAXGUSDT" else symbol
            result.append({
                "symbol": display_name,
                "price": float(item["price"])
            })
    return result

@app.get("/signals/vip")
def get_signals():
    prices_data = get_prices()
    if "error" in prices_data:
        return prices_data
        
    signals = []
    for item in prices_data:
        price = item["price"]
        symbol = item["symbol"]
        
        # Logic giả lập tín hiệu dựa trên giá thật
        confidence = random.randint(82, 98)
        side = "LONG" if random.random() > 0.45 else "SHORT"
        
        signals.append({
            "pair": symbol,
            "type": side,
            "entry": price,
            "sl": round(price * 0.985, 4) if side == "LONG" else round(price * 1.015, 4),
            "tp": round(price * 1.04, 4) if side == "LONG" else round(price * 0.96, 4),
            "confidence": confidence,
            "timestamp": int(time.time())
        })
    
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals
