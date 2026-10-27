.PHONY: setup test lint typecheck run eval demo clean ci spike

# ─── Setup ───
setup:
	python -m pip install --upgrade pip
	pip install -e "backend[dev]"

# ─── Quality ───
test:
	cd backend && python -m pytest tests/ -v --tb=short

lint:
	cd backend && python -m ruff check app/ tests/
	cd backend && python -m ruff format --check app/ tests/

typecheck:
	cd backend && python -m mypy app/mandate/ app/policy/ app/audit/ --strict

format:
	cd backend && python -m ruff format app/ tests/
	cd backend && python -m ruff check --fix app/ tests/

# ─── CI (runs all quality checks) ───
ci: lint typecheck test

# ─── Run ───
run:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ─── PayPal spike ───
spike:
	cd backend && python -m scripts.spike_paypal

# ─── Eval ───
eval:
	cd backend && python -m app.eval.runner
	cd backend && python -m app.eval.report

# ─── Demo ───
demo:
	cd backend && python -m scripts.seed_demo

# ─── Clean ───
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/*.db
