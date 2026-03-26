# ── Stage 1: Python deps ──────────────────────────────────────────────────────
FROM python:3.11-slim AS python-base

WORKDIR /app

# System deps needed by some Python packages (e.g. cffi, grpcio)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      gnupg \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Node.js + gws CLI ───────────────────────────────────────────────
FROM python-base AS final

# Install Node.js 20 LTS (needed for gws CLI + document engine pptxgenjs/docx)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install gws CLI globally via npm
RUN npm install -g @google/workspace-cli 2>/dev/null || \
    npm install -g gws 2>/dev/null || \
    true
# Fallback: ensure npx can find gws at runtime (npx gws auto-installs)
ENV GWS_CLI_PATH="npx --yes gws"

# ── Python dependencies ───────────────────────────────────────────────────────
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir anthropic langchain-anthropic openpyxl reportlab

# ── Application code ──────────────────────────────────────────────────────────
COPY backend/ /app/

WORKDIR /app

# Port Cloud Run expects
EXPOSE 8080

# Run with uvicorn on the Cloud Run port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
