FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-light.txt .
RUN pip install --no-cache-dir -r requirements-light.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
