.PHONY: test lint format security check

test:
	python -m pytest -q

lint:
	python -m ruff check .

format:
	python -m ruff format .

security:
	python -m bandit -r app -q

check:
	python -m ruff format --check .
	python -m ruff check .
	python -m bandit -r app -q
	python -m pytest -q
