# Stage 1: Build React 19 + TypeScript + Tailwind v4 + ECharts production bundle
FROM node:20-slim AS frontend-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Pure cross-platform FastAPI quantitative workbench runtime
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PORT=8000 \
    AGY2_DATA_DIR=/app/data \
    AGY2_SEED_DIR=/app/seed_data \
    PYTHONPATH=/app:/app/AGY2_FundAdvisory

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy backend code, docs, and built frontend assets
COPY AGY2_FundAdvisory/ ./AGY2_FundAdvisory/
COPY docs/ ./docs/
COPY --from=frontend-builder /app/web/dist ./web/dist

# Preserve public market baseline seeds outside /app/data so empty host volume mounts
# (- ./data:/app/data) NEVER shadow the 9 public seed files; auto-bootstrapped on startup.
COPY data/processed/aligned_matrix_total_return.parquet \
     data/processed/market_elite_nav_matrix.parquet \
     data/processed/market_elite_meta.parquet \
     data/processed/market_elite_sync_status.json \
     ./seed_data/processed/
COPY data/master/fund_catalog.parquet \
     data/master/fund_trading_rules.parquet \
     ./seed_data/master/
COPY data/macro/bond_zh_us_rate.parquet \
     data/macro/chinabond_yield_curve.parquet \
     ./seed_data/macro/
COPY data/mart/index_valuations.parquet \
     ./seed_data/mart/
COPY data/custom_sector_watchlist.json ./seed_data/

RUN mkdir -p /app/data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/v1/lakehouse/status" || exit 1

CMD ["sh", "-c", "exec uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 0.0.0.0 --port ${PORT}"]
