FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ml_worker/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ml_worker/ .

COPY app/config.py ./config.py

COPY app/models ./models

CMD ["python", "main.py"]