FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN python3 -m venv /opt/cubi-venv \
    && /opt/cubi-venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/cubi-venv/bin/python -m pip install --no-cache-dir -e . \
    && cd /app/apps/web \
    && npm install --no-audit --no-fund \
    && npm run build

ENV CUBI_PYTHON=/opt/cubi-venv/bin/python \
    PYTHONPATH=/app/src \
    CUBI_PREVIEW_ALLOW_LAN=1 \
    CUBI_PREVIEW_PUBLIC_DEMO=1 \
    HOST=0.0.0.0

EXPOSE 10000

CMD ["sh", "-c", "node apps/web/preview-full.mjs --host 0.0.0.0 --port ${PORT:-10000}"]
