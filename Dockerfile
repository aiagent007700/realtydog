FROM python:3.12-slim

WORKDIR /app

# System deps: psycopg2 build + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Railway overrides the port via $PORT in railway.toml; 8000 is the local default.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
