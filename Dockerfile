FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    bash \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth-app .

ENV OLLAMA_HOST=0.0.0.0
ENV PYTHONPATH=/app

RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'echo "Starting Ollama..."' >> /app/start.sh && \
    echo 'ollama serve &' >> /app/start.sh && \
    echo 'OLLAMA_PID=$!' >> /app/start.sh && \
    echo 'echo "Waiting for Ollama to start..."' >> /app/start.sh && \
    echo 'sleep 5' >> /app/start.sh && \
    echo 'echo "Downloading model..."' >> /app/start.sh && \
    echo 'ollama pull gemma3n:e4b' >> /app/start.sh && \
    echo 'echo "Starting FastAPI..."' >> /app/start.sh && \
    echo 'python -m uvicorn main:app --host 0.0.0.0 --port 8000' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 8000

CMD ["/bin/bash", "/app/start.sh"]
