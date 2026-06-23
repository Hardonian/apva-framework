FROM python:3.12-slim

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1
ENV WORKDIR=/app

WORKDIR ${WORKDIR}

# Install system dependencies if required by pg or building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

# Resolve and install dependencies using uv
RUN uv pip install --system -r pyproject.toml

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
