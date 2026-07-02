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

COPY . .

# Resolve and install dependencies using uv
RUN uv pip install --system -e .

EXPOSE 8000

CMD ["uvicorn", "apps.backend.apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
