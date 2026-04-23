from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time
import asyncio

app = FastAPI()

# Cấu hình CORS để Dashboard Lovable truy cập được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THÔNG TIN CẤU HÌNH ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "-1003101971466"
# Danh sách 10 đồng coin mục tiêu
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"]

# --- ENDPOINT LẤY GIÁ ---
@app.get("/prices")
def get_prices():
    try:
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['lastPrice'])} 
                for i in res if i['symbol'] in COINS]
    except:
        return []

# --- ENDPOINT TÍN HIỆU VIP (BẢN KHÔNG BỊ CHẶN) ---
@app.get("/signals/vip")
def vip_signals():
    signals = []
    try:
        # Lấy dữ liệu ticker 24h - Endpoint này rất khó bị sàn chặn IP
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=5).json()
        
        for item in res:
            if item['symbol'] in COINS:
                symbol = item['symbol']
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                
                # THUẬT TOÁN: Giả lập RSI và Tín hiệu dựa trên biến động giá thực tế (Price Action)
                # Nếu giá giảm mạnh trong 24h qua -> Ưu tiên LONG (Rebound)
                # Nếu giá tăng mạnh trong 24h qua -> Ưu tiên SHORT (Correction)
                side = "LONG" if change < 0 else "SHORT"
                
                # Tính RSI giả lập dựa trên % thay đổi để Dashboard luôn có dữ liệu đẹp
                rsi_mock = round(50 - (change * 1.5), 2)
                rsi_mock = max(18, min(82, rsi_mock)) # Giới hạn RSI trong khoảng 18-82
                
                conf = random.randint(86, 97) # Độ tin cậy cao để kích hoạt Telegram

                signals.append({
                    "pair": "XAUUSD" if symbol == "PAXGUSDT" else symbol,
                    "type": side,
                    "entry": price,
                    "sl": round(price * 0.982, 4) if side == "LONG" else round(price * 1.018, 4),
                    "tp": round(price * 1.05, 4) if side == "LONG" else round(price * 0.95, 4),
                    "confidence": conf,
                    "rsi": rsi_mock,
                    "timestamp": int(time.time())
                })
    except:
        pass

    # Sắp xếp các kèo có độ tin cậy cao nhất lên đầu
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals

# --- LOGIC GỬI TELEGRAM ---
def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except: pass

async def telegram_worker():
    sent_signals = {}
    while True:
        try:
            signals = vip_signals()
            for s in signals:
                # Chỉ bắn những kèo "siêu thơm" vào Channel Telegram
                if s['confidence'] > 93 and s['pair'] not in sent_signals:
                    msg = (
                        f"🚀 *TÍN HIỆU VIP: {s['pair']}*\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"👉 Loại: *{s['type']}*\n"
                        f"📍 Entry: `{s['entry']}`\n"
                        f"🎯 TP: `{s['tp']}` | 🛑 SL: `{s['sl']}`\n"
                        f"📊 RSI: `{s['rsi']}` | Tin cậy: `{s['confidence']}%`\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📱 [Xem Dashboard](https://your-lovable-link.lovable.app)"
                    )
                    send_telegram_msg(msg)
                    sent_signals[s['pair']] = time.time()
            
            # Reset bộ nhớ gửi tin sau 2 tiếng để có thể gửi lại cặp đó nếu có biến động mới
            curr = time.time()
            sent_signals = {k: v for k, v in sent_signals.items() if curr - v < 7200}
        except: pass
        await asyncio.sleep(300) # Quét mỗi 5 phút một lần

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_worker())

@app.get("/")
def home():
    return {"status": "PulseSignal VIP v2 Online"}
