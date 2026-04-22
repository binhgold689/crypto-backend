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

@app.get("/")
def home():
    return {"message": "Server is running"}

@app.get("/prices")
def get_prices():
    try:
        # Tăng timeout lên 15 giây để tránh lỗi mạng chậm
        response = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=15)
        
        # Kiểm tra nếu API Binance trả về lỗi (ví dụ lỗi 429 do gọi quá nhiều)
        if response.status_code != 200:
            return {"error": f"Binance API returned status {response.status_code}"}
            
        data = response.json()
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

    except requests.exceptions.RequestException as e:
        # Trả về lỗi chi tiết nếu do kết nối mạng
        return {"error": "Connection Error", "details": str(e)}
    except Exception as e:
        # Trả về lỗi khác nếu có
        return {"error": "System Error", "details": str(e)}

@app.get("/signals/vip")
def get_signals():
    # Gọi hàm get_prices để tận dụng logic xử lý lỗi ở trên
    prices_data = get_prices()
    
    if isinstance(prices_data, dict) and "error" in prices_data:
        return prices_data # Trả về lỗi nếu không lấy được giá
        
    signals = []
    for item in prices_data:
        price = item["price"]
        symbol = item["symbol"]
        
        confidence = random.randint(80, 98)
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
