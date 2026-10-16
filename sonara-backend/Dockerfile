FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 SONARA_DATA_DIR=/data/jobs SONARA_MODEL_CACHE=/data/models
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-light.txt .
RUN pip install -r requirements-light.txt
RUN useradd --uid 10001 --create-home sonara \
    && mkdir -p /data/jobs /data/models && chown -R sonara:sonara /data
COPY --chown=sonara:sonara . .
USER sonara
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
