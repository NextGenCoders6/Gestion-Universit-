# ERP UCCB — image de production : interface React construite + Django servi par gunicorn.
#
#   docker compose up -d --build        (depuis erp/, voir docker/README.md)

# ── 1. Interface React (Vite) ────────────────────────────────────
FROM node:22-alpine AS interface
WORKDIR /erp/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# vite.config.js écrit le build dans ../backend/frontend_dist
RUN mkdir -p ../backend && npm run build

# ── 2. Dépendances Python (compilation de mysqlclient) ───────────
FROM python:3.12-slim AS dependances
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt

# ── 3. Image finale ──────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
# libmariadb3 : client MySQL de mysqlclient ; polices DejaVu : textes des PDF.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libmariadb3 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 erp
COPY --from=dependances /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels

WORKDIR /app
COPY --chown=erp:erp backend/ ./
COPY --from=interface --chown=erp:erp /erp/backend/frontend_dist ./frontend_dist
COPY --chown=erp:erp docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/media /app/staticfiles && chown erp:erp /app/media /app/staticfiles

USER erp
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
