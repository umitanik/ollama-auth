FROM ubuntu:24.04

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt --break-system-packages

COPY auth-app .

ENV OLLAMA_HOST=0.0.0.0
ENV PYTHONPATH=/app

RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'echo "Starting Ollama..."' >> /app/start.sh && \
    echo 'ollama serve &' >> /app/start.sh && \
    echo 'OLLAMA_PID=$!' >> /app/start.sh && \
    echo 'echo "Waiting for Ollama to start..."' >> /app/start.sh && \
    echo 'sleep 15' >> /app/start.sh && \
    echo 'echo "Downloading model..."' >> /app/start.sh && \
    echo 'ollama pull gemma3n:e4b' >> /app/start.sh && \
    echo 'echo "Starting FastAPI..."' >> /app/start.sh && \
    echo 'python3 -m uvicorn main:app --host 0.0.0.0 --port 8000' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 8000

CMD ["/bin/bash", "/app/start.sh"]
