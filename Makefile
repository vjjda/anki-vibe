# Path: Makefile
.PHONY: install format lint type-check run clean

install:
	poetry install

format:
	poetry run black src
	poetry run ruff check --fix src

lint:
	poetry run ruff check src

type-check:
	poetry run mypy src

# Ví dụ chạy: make run ARGS="sync --profile UserA"
run:
	poetry run python src/main.py $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete