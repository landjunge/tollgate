# Portable Tollgate image — secrets via volume or env, not baked in.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8787 \
    TOLLGATE_PORTABLE=1 \
    TOLLGATE_HOME=/data

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

# Data dir for Key.txt / keys_app.json / ledger
VOLUME ["/data"]
EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "tollgate.server_v1:app", "--host", "0.0.0.0", "--port", "8787"]
