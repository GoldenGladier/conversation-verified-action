from fastapi import FastAPI
from app.telegram.bot import create_bot

app = FastAPI(title="Admin Agent", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "admin-agent"
    }

telegram_bot = create_bot()