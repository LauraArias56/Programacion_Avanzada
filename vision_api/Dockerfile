FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision \
    && pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY src ./src
COPY artifacts ./artifacts

EXPOSE 8100

HEALTHCHECK --interval=15s --timeout=5s --retries=10 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')"

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8100"]
