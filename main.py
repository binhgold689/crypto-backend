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

# Danh sách coin (MEXC dùng định dạng giống Binance: BTCUSDT)
COINS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "PAXGUSDT", # Gold
    "ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","DOTUSDT",
    "LINKUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","FILUSDT"
]

@app.get("/")
def home():
    return {"message": "PulseSignal VIP Online - MEXC Data Source Enabled"}

@app.get("/prices")
def get_prices():
    try:
        # Sử dụng API của sàn MEXC - Rất ít khi chặn IP
        url = "https://api.mexc.com/api/v3/ticker/price"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return {"error": f"MEXC API returned {response.status_code}"}
            
        data = response.json()
        result = []
        
        # MEXC trả về danh sách các dict {'symbol': '...', 'price': '...'}
        for item in data:
            symbol = item.get("symbol")
            if symbol in COINS:
                display_name = "XAUUSD" if symbol == "PAXGUSDT" else symbol
                result.append({
                    "symbol": display_name,
                    "price": float(item["price"])
                })
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/signals/vip")
def get_signals():
    prices_data = get_prices()
    if isinstance(prices_data, dict) and "error" in prices_data:
        return prices_data
        
    signals = []
    for item in prices_data:
        price = item["price"]
        symbol = item["symbol"]
        
        # Logic giả lập tín hiệu
        confidence = random.randint(85, 99)
        side = "LONG" if random.random() > 0.5 else "SHORT"
        
        signals.append({
            "pair": symbol,
            "type": side,
            "entry": price,
            "sl": round(price * 0.98, 4) if side == "LONG" else round(price * 1.02, 4),
            "tp": round(price * 1.05, 4) if side == "LONG" else round(price * 0.95, 4),
            "confidence": confidence,
            "timestamp": int(time.time())
        })
    return signals
