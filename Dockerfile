# Multi-stage build: build the React client, then run the API that serves it.
# The result is ONE container: FastAPI serves the API and the built SPA together.

# --- stage 1: build the web client -----------------------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build   # -> /web/dist

# --- stage 2: the Python app -----------------------------------------------
FROM python:3.11-slim AS app
WORKDIR /app

# uv for fast, locked installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install deps first (cached unless the lock changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# App code + the built client from stage 1.
COPY agent/ ./agent/
COPY server.py cli.py ./
COPY --from=web /web/dist ./web/dist

EXPOSE 8000
# One worker keeps the in-memory SessionStore coherent. To scale out, externalize
# sessions (Redis) and raise workers/replicas; see docs/SCALING.md.
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
