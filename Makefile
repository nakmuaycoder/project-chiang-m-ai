.PHONY: install run format check clean

# ==========================================
# 🛠️ INSTALLATION
# ==========================================
install:
	@echo "📦 Installation des dépendances avec uv..."
	uv sync
	@echo "🪝 Installation des hooks Git (Pre-commit)..."
	uv run pre-commit install
	@echo "🔒 Vérification du fichier de secrets..."
	@if [ ! -f .secrets.baseline ]; then \
		echo "   -> Génération de .secrets.baseline..."; \
		uv run detect-secrets scan > .secrets.baseline; \
	else \
		echo "   -> .secrets.baseline existe déjà (on ne touche à rien)."; \
	fi
	@echo "✅ Environnement prêt ! Tu peux coder."


run:
	uv run main.py


# Formate tout le code (Ruff) sans attendre le commit
format:
	uv run ruff format .
	uv run ruff check --fix .

# Juste vérifier s'il y a des erreurs (sans modifier)
check:
	uv run ruff check .

# Supprime l'environnement virtuel et les caches
clean:
	rm -rf .venv
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +