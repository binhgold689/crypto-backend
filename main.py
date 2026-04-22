from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/price/{symbol}")
def price(symbol: str):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
    return requests.get(url).json()
