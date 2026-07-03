.PHONY: install install-local check lint format test ingest ingest-debug rag mcp

# Standard install (CPU torch — matches CI and production)
install:
	poetry install

# Local dev install: CPU torch first, then CUDA override if GPU present
install-local: install
	@if command -v nvidia-smi > /dev/null 2>&1; then \
		echo "GPU detected — installing CUDA torch (cu128)..."; \
		poetry run pip install torch --index-url https://download.pytorch.org/whl/cu128 --force-reinstall; \
	else \
		echo "No GPU detected — CPU torch from lockfile"; \
	fi

check:
	PRE_COMMIT_NO_CONCURRENCY=1 poetry run pre-commit run --all-files
	poetry run pytest --cov=linguaalayam --cov-fail-under=80

lint:
	poetry run ruff check --fix .
	poetry run interrogate --config=pyproject.toml .

format:
	poetry run ruff format .

test:
	poetry run pytest --cov=linguaalayam --cov-report=term-missing -q

ingest:
	poetry run ingest

ingest-debug:
	poetry run ingest corpus=debug

rag:
	poetry run rag 'rag.query=$(QUERY)' llm=nollm

mcp:
	poetry run mcp-server
