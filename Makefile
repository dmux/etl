.DEFAULT_GOAL := help
UV := uv

.PHONY: help
help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Instala dependências e registra os hooks de git
	$(UV) sync
	$(UV) run pre-commit install --install-hooks
	$(UV) run pre-commit install --hook-type pre-push

.PHONY: fmt
fmt: ## Formata o código
	$(UV) run ruff format src tests tools
	$(UV) run ruff check --fix src tests tools

.PHONY: lint
lint: ## Linter + type check
	$(UV) run ruff check src tests tools
	$(UV) run ruff format --check src tests tools
	$(UV) run mypy

.PHONY: test
test: ## Testes rápidos (unit + integration, sem e2e)
	$(UV) run pytest -m "not e2e"

.PHONY: cov
cov: ## Testes com o gate de cobertura de 95%
	$(UV) run pytest -m "not e2e" --cov --cov-report=term-missing

.PHONY: e2e
e2e: ## Testes contra o minilake real (exige `make up`)
	$(UV) run pytest -m e2e

.PHONY: check
check: lint cov ## Gate completo: lint + type check + cobertura

.PHONY: hooks
hooks: ## Roda o pre-commit em todos os arquivos
	$(UV) run pre-commit run --all-files

.PHONY: up
up: ## Sobe o minilake
	cd ../minilake && docker compose up -d
	@echo "minilake: http://localhost:8000/_minilake/health"

.PHONY: down
down: ## Derruba o minilake
	cd ../minilake && docker compose down
