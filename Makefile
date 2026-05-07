.PHONY: lint test run build-docker help

help:
	@echo "Available targets:"
	@echo "  lint         - Run ruff format check and lint"
	@echo "  test         - Run pytest"
	@echo "  run          - Run the application locally"
	@echo "  build-docker - Build Docker image"
	@echo "  run-docker   - Run Docker container"

lint:
	@echo "=== Running Ruff Format Check ==="
	uv run ruff format --check .
	@echo "=== Running Ruff Lint ==="
	uv run ruff check .
	@echo "=== Running MyPy ==="
	uv run mypy whodis/

test:
	@echo "=== Running Tests ==="
	uv run pytest -v --tb=short

run:
	@echo "=== Starting Application ==="
	uv run uvicorn whodis.main:app --host 0.0.0.0 --port 8000 --reload

build-docker:
	@echo "=== Building Docker Image ==="
	docker build -t whodis:latest .

run-docker:
	@echo "=== Running Docker Container ==="
	docker run -p 8000:8000 -v $(PWD)/uploads:/app/uploads whodis:latest
