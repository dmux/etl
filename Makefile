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
e2e: ## Testes contra o ministack real (exige `make up`)
	$(UV) run pytest -m e2e

.PHONY: check
check: lint cov ## Gate completo: lint + type check + cobertura

.PHONY: hooks
hooks: ## Roda o pre-commit em todos os arquivos
	$(UV) run pre-commit run --all-files

GLUE_IMAGE := ghcr.io/dmux/openarchflow/ministack_glue_libs_4.0.0_image_01:latest

.PHONY: up
up: ## Sobe o ministack com o executor de jobs Glue (exige Docker)
	docker pull --platform linux/amd64 $(GLUE_IMAGE)
	@if docker ps --format '{{.Names}}' | grep -qx ministack; then echo "ministack já está de pé"; else \
		docker run -d --name ministack -p 4566:4566 \
			-v /var/run/docker.sock:/var/run/docker.sock \
			-e GLUE_DOCKER_IMAGE=$(GLUE_IMAGE) -e S3_PERSIST=1 \
			ministackorg/ministack:full; fi
	@echo "ministack: http://localhost:4566/_ministack/health"

.PHONY: down
down: ## Derruba o ministack
	docker rm -f ministack
