import logging
import os
import time
from collections import defaultdict

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ollama Gemma3n Secure Auth API")
security = HTTPBearer()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
VALID_TOKEN = os.getenv("AUTH_TOKEN", "SECRET_TOKEN")
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "50"))

user_requests = defaultdict(lambda: {"count": 0, "reset_time": time.time()})

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    model: str = Field(default="gemma3n:e4b", pattern="^[a-zA-Z0-9_:-]+$")

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Mesaj boş olamaz')

        dangerous_chars = ['<script', '<?php', 'javascript:', 'data:']
        for char in dangerous_chars:
            if char.lower() in v.lower():
                raise ValueError('Güvenlik riski: Tehlikeli karakter bulundu')
        return v.strip()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != VALID_TOKEN:
        logger.warning("SECURITY_ALERT: Invalid token attempt")
        raise HTTPException(status_code=401, detail="Geçersiz token")
    return True


def rate_limit_check(request: Request):
    client_ip = request.client.host
    current_time = time.time()

    if current_time > user_requests[client_ip]["reset_time"]:
        user_requests[client_ip] = {
            "count": 0,
            "reset_time": current_time + 3600
        }

    if user_requests[client_ip]["count"] >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {RATE_LIMIT_PER_HOUR}/hour")

    user_requests[client_ip]["count"] += 1
    return True


@app.get("/")
async def root():
    return {"message": "Ollama Gemma3n Secure Auth API", "version": "2.0-secure"}


@app.post("/chat")
async def chat(
        request: ChatRequest,
        http_request: Request,
        authorized: bool = Depends(verify_token),
        rate_limited: bool = Depends(rate_limit_check)
):
    # Security logging
    logger.info(f"CHAT_REQUEST: IP={http_request.client.host}, Model={request.model}, MsgLen={len(request.message)}")

    try:
        models_response = requests.get(f"{OLLAMA_URL}/api/tags")
        if models_response.status_code != 200:
            pull_response = requests.post(f"{OLLAMA_URL}/api/pull",
                                          json={"name": request.model})
            if pull_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Model indirilemedi")

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": request.model,
                "prompt": request.message,
                "stream": False
            }
        )

        if response.status_code == 200:
            logger.info("CHAT_SUCCESS: Request completed")
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Ollama API hatası")

    except requests.exceptions.ConnectionError:
        logger.error("CHAT_ERROR: Ollama connection failed")
        raise HTTPException(status_code=503, detail="Ollama servisine bağlanılamıyor")
    except Exception as e:
        logger.error(f"CHAT_ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@app.get("/models")
async def get_models(authorized: bool = Depends(verify_token)):
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@app.get("/health")
async def health():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        status = "healthy" if response.status_code == 200 else "unhealthy"
        return {"status": status, "ollama_connection": OLLAMA_URL}
    except Exception as e:
        return {"status": "unhealthy", "ollama_connection": "disconnected", "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
