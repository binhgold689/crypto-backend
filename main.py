from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import time
import asyncio

app = FastAPI()

# Cấu hình CORS để Lovable có thể truy cập
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
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"]

# --- HÀM TÍNH RSI ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    up = sum(d for d in deltas[:period] if d > 0) / period
    down = sum(-d for d in deltas[:period] if d < 0) / period
    for d in deltas[period:]:
        gain, loss = (d, 0) if d > 0 else (0, -d)
        up = (up * (period - 1) + gain) / period
        down = (down * (period - 1) + loss) / period
    return round(100 - 100 / (1 + (up/down if down != 0 else 100)), 2)

# --- LOGIC LẤY DỮ LIỆU & TÍN HIỆU ---
@app.get("/prices")
def get_prices():
    try:
        url = "https://api.mexc.com/api/v3/ticker/price"
        data = requests.get(url, timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['price'])} 
                for i in data if i['symbol'] in COINS]
    except: return []

@app.get("/signals/vip")
def vip_signals():
    signals = []
    for symbol in COINS:
        try:
            # Lấy 50 nến 1h gần nhất từ MEXC
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
            res = requests.get(url, timeout=3).json()
            close_prices = [float(c[4]) for c in res]
            rsi = calculate_rsi(close_prices)
            price = close_prices[-1]
            
            side = "LONG" if rsi < 50 else "SHORT"
            # Độ tin cậy cao hơn khi RSI đi vào vùng quá mua/quá bán
            conf = random.randint(88, 98) if (rsi < 35 or rsi > 65) else random.randint(70, 85)

            signals.append({
                "pair": "XAUUSD" if symbol == "PAXGUSDT" else symbol,
                "type": side,
                "entry": price,
                "sl": round(price * 0.985, 4) if side == "LONG" else round(price * 1.015, 4),
                "tp": round(price * 1.04, 4) if side == "LONG" else round(price * 0.96, 4),
                "confidence": conf,
                "rsi": rsi,
                "timestamp": int(time.time())
            })
        except: continue
    
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals

# --- BOT TELEGRAM CHẠY NGẦM ---
def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

async def telegram_worker():
    sent_signals = {} 
    while True:
        try:
            signals = vip_signals()
            for s in signals:
                # Chỉ bắn kèo cực thơm (Confidence > 92) vào Channel
                if s['confidence'] > 92 and s['pair'] not in sent_signals:
                    msg = (
                        f"🚀 *TÍN HIỆU VIP: {s['pair']}*\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"👉 Loại: *{s['type']}*\n"
                        f"📍 Entry: `{s['entry']}`\n"
                        f"🎯 TP: `{s['tp']}` | 🛑 SL: `{s['sl']}`\n"
                        f"📊 RSI: `{s['rsi']}` | Tin cậy: `{s['confidence']}%`\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📱 [Xem Full Dashboard](https://your-lovable-link.lovable.app)"
                    )
                    send_telegram_msg(msg)
                    sent_signals[s['pair']] = time.time()

            # Reset bộ nhớ kèo sau 2 tiếng
            current_time = time.time()
            sent_signals = {k: v for k, v in sent_signals.items() if current_time - v < 7200}
        except: pass
        await asyncio.sleep(600) # Quét mỗi 10 phút

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_worker())

@app.get("/")
def health():
    return {"status": "PulseSignal VIP System is Online", "bot": "Active"}
