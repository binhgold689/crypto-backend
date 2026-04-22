from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time

app = FastAPI()

# ===== CẤU HÌNH CORS (BẮT BUỘC ĐỂ LOVABLE TRUY CẬP ĐƯỢC) =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== DANH SÁCH 50 COIN VIP + GOLD =====
COINS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "PAXGUSDT", # Đây là Gold (Vàng) - Sẽ được đổi tên hiển thị thành XAUUSD
    "ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","DOTUSDT",
    "LINKUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","FILUSDT","APTUSDT","ARBUSDT","OPUSDT",
    "INJUSDT","SUIUSDT","SEIUSDT","PEPEUSDT","SHIBUSDT",
    "UNIUSDT","AAVEUSDT","MKRUSDT","RUNEUSDT","GRTUSDT",
    "ALGOUSDT","VETUSDT","ICPUSDT","SANDUSDT","MANAUSDT",
    "AXSUSDT","FLOWUSDT","EGLDUSDT","THETAUSDT","KASUSDT",
    "TIAUSDT","JUPUSDT","WIFUSDT","BONKUSDT","FTMUSDT",
    "HBARUSDT","EOSUSDT","XTZUSDT","GALAUSDT"
]

# ===== HÀM HỖ TRỢ LẤY DỮ LIỆU TỪ BINANCE =====
def get_binance_data():
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Lỗi kết nối Binance: {e}")
        return []

# ===== TRANG CHỦ =====
@app.get("/")
def home():
    return {"status": "PulseSignal VIP System Online", "update": "Real-time Gold & Crypto"}

# ===== ENDPOINT 1: LẤY GIÁ REALTIME =====
@app.get("/prices")
def get_prices():
    data = get_binance_data()
    result = []
    
    for item in data:
        symbol = item.get("symbol")
        if symbol in COINS:
            # Đổi tên PAXGUSDT thành XAUUSD cho chuyên nghiệp
            display_name = "XAUUSD" if symbol == "PAXGUSDT" else symbol
            result.append({
                "symbol": display_name,
                "price": float(item["price"])
            })
    
    return result

# ===== ENDPOINT 2: TÍN HIỆU VIP (50 COIN) =====
@app.get("/signals/vip")
def get_vip_signals():
    data = get_binance_data()
    signals = []
    
    for item in data:
        symbol = item.get("symbol")
        if symbol in COINS:
            price = float(item["price"])
            display_name = "XAUUSD" if symbol == "PAXGUSDT" else symbol
            
            # Logic tạo tín hiệu (Có thể thay thế bằng Indicator thật sau này)
            rsi_sim = random.randint(20, 80)
            side = "LONG" if rsi_sim < 48 else "SHORT"
            confidence = random.randint(75, 99)
            
            # Tính toán SL/TP (Long ăn 3% lỗ 1%, Short ngược lại)
            if side == "LONG":
                tp = round(price * 1.03, 4)
                sl = round(price * 0.985, 4)
            else:
                tp = round(price * 0.97, 4)
                sl = round(price * 1.015, 4)
                
            signals.append({
                "pair": display_name,
                "type": side,
                "entry": price,
                "sl": sl,
                "tp": tp,
                "confidence": confidence,
                "rsi": rsi_sim,
                "timestamp": int(time.time())
            })
            
    # Sắp xếp tín hiệu có độ tin cậy cao nhất lên đầu
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals

# ===== ENDPOINT 3: TÍN HIỆU FREE (LẤY 5 CÁI NGẪU NHIÊN) =====
@app.get("/signals/free")
def get_free_signals():
    all_signals = get_vip_signals()
    return all_signals[:5]

# ===== ENDPOINT 4: THỐNG KÊ DASHBOARD =====
@app.get("/summary")
def get_summary():
    return {
        "active_signals": len(COINS),
        "win_rate": "76.4%",
        "roi_30d": "+41.2%",
        "server_time": int(time.time())
    }
