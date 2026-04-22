from fastapi import FastAPI
import random

app = FastAPI()

@app.get("/")
def home():
    return {"status":"running"}

@app.get("/signals")
def signals():
    return [
        {
            "pair":"BTCUSDT",
            "type":"LONG",
            "entry":68400,
            "sl":67800,
            "tp":69500,
            "confidence":87
        },
        {
            "pair":"ETHUSDT",
            "type":"SHORT",
            "entry":3480,
            "sl":3560,
            "tp":3320,
            "confidence":82
        }
    ]
