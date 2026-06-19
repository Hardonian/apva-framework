FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY apps/mock_target/requirements.txt /build/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /build/requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY --from=builder /install /usr/local
COPY apps/mock_target /app/apps/mock_target

EXPOSE 8080
CMD ["uvicorn", "apps.mock_target.main:app", "--host", "0.0.0.0", "--port", "8080"]
