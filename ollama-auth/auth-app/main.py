from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
import uvicorn

app = FastAPI(title="Ollama Gemma3n Auth API")
security = HTTPBearer()

OLLAMA_URL = f"http://localhost:11434"
VALID_TOKEN = "myAuthToken2025"

class ChatRequest(BaseModel):
    message: str
    model: str = "gemma3n:e4b"

class LoginRequest(BaseModel):
    username: str
    password: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != VALID_TOKEN:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    return True

@app.get("/")
async def root():
    return {"message": "Ollama Gemma3n Auth API"}

@app.post("/chat")
async def chat(request: ChatRequest):
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
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Ollama API hatası")

    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama servisine bağlanılamıyor")
    except Exception as e:
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