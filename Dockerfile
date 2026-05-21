# ── OTD ERP 模擬層 Dockerfile ──────────────────────────────
FROM python:3.9-slim

WORKDIR /app

# ── 建置時注入 commit hash ─────────────────────────────────────
ARG GIT_COMMIT=unknown
RUN echo "${GIT_COMMIT}" > /app/GIT_COMMIT

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8004/healthz')"

EXPOSE 8004
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]