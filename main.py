from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
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
    "ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","DOTUSDT","LINKUSDT"
]

# --- HÀM TÍNH RSI CHUẨN ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    seed = deltas[:period]
    up = sum(d for d in seed if d > 0) / period
    down = sum(-d for d in seed if d < 0) / period
    
    if down == 0: return 100
    rs = up / down
    rsi = [100 - 100 / (1 + rs)]
    
    for d in deltas[period:]:
        gain = d if d > 0 else 0
        loss = -d if d < 0 else 0
        up = (up * (period - 1) + gain) / period
        down = (down * (period - 1) + loss) / period
        if down == 0: rs = 100
        else: rs = up / down
        rsi.append(100 - 100 / (1 + rs))
        
    return round(rsi[-1], 2)

# --- LẤY DỮ LIỆU NẾN TỪ MEXC (VÌ BINANCE CHẶN IP) ---
def get_mexc_signals():
    signals = []
    for symbol in COINS:
        try:
            # Lấy 100 nến gần nhất hệ 1 giờ (1h)
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
            res = requests.get(url, timeout=5).json()
            
            # Giá đóng cửa là phần tử thứ 4 trong mỗi cây nến
            close_prices = [float(candle[4]) for candle in res]
            current_price = close_prices[-1]
            
            rsi_value = calculate_rsi(close_prices)
            
            # Logic quyết định tín hiệu
            if rsi_value < 35:
                side = "LONG"
                confidence = random_int(85, 95) # RSI thấp thì tin tưởng Long cao
            elif rsi_value > 65:
                side = "SHORT"
                confidence = random_int(85, 95)
            else:
                side = "LONG" if rsi_value < 50 else "SHORT"
                confidence = random_int(60, 80)

            display_name = "XAUUSD" if symbol == "PAXGUSDT" else symbol
            
            signals.append({
                "pair": display_name,
                "type": side,
                "entry": current_price,
                "sl": round(current_price * 0.98, 4) if side == "LONG" else round(current_price * 1.02, 4),
                "tp": round(current_price * 1.05, 4) if side == "LONG" else round(current_price * 0.95, 4),
                "confidence": confidence,
                "rsi": rsi_value,
                "timestamp": int(time.time())
            })
        except:
            continue
    return signals

def random_int(a, b):
    # Hàm hỗ trợ tạo số ngẫu nhiên nhẹ cho Confidence
    import random
    return random.randint(a, b)

@app.get("/prices")
def get_prices():
    try:
        url = "https://api.mexc.com/api/v3/ticker/price"
        data = requests.get(url).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['price'])} 
                for i in data if i['symbol'] in COINS]
    except: return {"error": "API Error"}

@app.get("/signals/vip")
def vip_signals():
    data = get_mexc_signals()
    # Sắp xếp các kèo có RSI cực đoan (ngon nhất) lên đầu
    data.sort(key=lambda x: x["confidence"], reverse=True)
    return data

@app.get("/")
def health():
    return {"status": "Smart RSI Engine Running"}
