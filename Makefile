.PHONY: install run format check clean test

# ==========================================
# 🛠️ INSTALLATION
# ==========================================
install:
	@echo "📦 Installing dependencies with uv..."
	uv sync
	@echo "🪝 Installing Git hooks (Pre-commit)..."
	uv run pre-commit install
	@echo "🔒 Checking secrets baseline..."
	@if [ ! -f .secrets.baseline ]; then \
		echo "   -> Generating .secrets.baseline..."; \
		uv run detect-secrets scan > .secrets.baseline; \
	else \
		echo "   -> .secrets.baseline already exists (skipping)."; \
	fi
	@echo "✅ Environment ready! Happy coding."


run:
	uv run python -m project_chiang_m_ai sync --block


# Format all code (Ruff) without waiting for commit
format:
	uv run ruff format .
	uv run ruff check --fix .

# Only check for errors (without modifying)
check:
	uv run ruff check .

# Remove virtual environment and caches
clean:
	rm -rf .venv
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Run tests with pytest
test:
	@echo "🧪 Running tests..."
	uv run pytest
