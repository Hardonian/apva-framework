# APVA Framework Task Runner (Justfile)
# Install just: cargo install just OR pip install rust-just

# Install and synchronize all dependencies
bootstrap:
    uv sync --all-extras

# Run the local backend API server with auto-reload
dev:
    uv run uvicorn apps.backend.apps.backend.main:app --reload --host 127.0.0.1 --port 8000

# Run all test suites
test:
    uv run pytest tests/ -v --tb=short

# Run tests with code coverage report
test-coverage:
    uv run pytest tests/ --cov=apva --cov-report=term-missing

# Lint code using ruff
lint:
    uv run ruff check .

# Format code using ruff
format:
    uv run ruff format .

# Run static type checking
type-check:
    uv run mypy apva/ --ignore-missing-imports

# Run health check against local API
smoke:
    curl -fsS http://127.0.0.1:8000/api/v1/health || echo "No API running on 127.0.0.1:8000"

# Run built-in APVA demo benchmark simulation
demo:
    uv run apva demo

# Run enterprise AI ROI audit scorecard
audit:
    uv run apva audit --golden-set data/golden_dataset.json

# Run CI/CD golden set evaluation gate
eval-gate:
    uv run apva run-eval --golden-set data/golden_dataset.json --threshold 0.85

# Validate golden dataset schema
validate-dataset:
    uv run apva validate --golden-set data/golden_dataset.json

# Spin up full Docker Compose stack
docker-up:
    docker compose up -d --build

# Tear down Docker Compose stack
docker-down:
    docker compose down -v
