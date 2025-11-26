FROM python:3.11-slim

LABEL maintainer="AI Trader"
LABEL description="AI-powered cryptocurrency trading bot"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

COPY requirements.txt .

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/data/cache /app/config

VOLUME ["/app/logs", "/app/data", "/app/config"]

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
