.DEFAULT_GOAL := help
UV := uv
RAIZ := ../..
# Commit fixo da fonte (ADR-002). Atualizar a fonte é trocar este hash, com intenção.
FONTE_URL := https://github.com/openfootball/south-america.git
FONTE_COMMIT := 119fa1724b2079a1072a0cb0ca0ccac26d92fd34

.PHONY: help
help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Instala dependências
	$(UV) sync

.PHONY: fonte
fonte: ## Clona o openfootball no commit fixo, em south-america/ (somente leitura)
	@if [ ! -d south-america/.git ]; then git clone -q $(FONTE_URL) south-america; fi
	git -C south-america fetch -q --depth 1 origin $(FONTE_COMMIT)
	git -C south-america checkout -q $(FONTE_COMMIT)
	@echo "fonte em $$(git -C south-america rev-parse --short HEAD)"

.PHONY: fmt
fmt: ## Formata o código
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

.PHONY: lint
lint: ## Linter + type check
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests
	$(UV) run mypy

.PHONY: test
test: ## Testes rápidos, sem e2e
	$(UV) run pytest -m "not e2e"

.PHONY: cov
cov: ## Testes com o gate de cobertura de 95%
	$(UV) run pytest -m "not e2e" --cov --cov-report=term-missing

.PHONY: check
check: lint guardas cov ## Gate completo: lint + type check + guardas + cobertura

GUARDAS := hexagonal-imports spark-no-driver-collect spark-no-print glue-sessao \
	athena-sql-dialect spark-no-select-star glossario sem-excecao-engolida

.PHONY: guardas
guardas: ## Roda as 8 guardas de pipeline da raiz, com o glossário deste exemplo
	@arquivos=$$(find src tests -name '*.py'); falhou=0; \
	for guarda in $(GUARDAS); do \
		$(UV) run python $(RAIZ)/tools/precommit/guardas_spark.py --guarda $$guarda \
			--glossario glossario.toml $$arquivos || falhou=1; \
	done; \
	if [ $$falhou -eq 0 ]; then echo "guardas: 8 de 8 passaram"; fi; exit $$falhou

# ---------------------------------------------------------------- ministack (ADR-009)
GLUE := scripts/glue.sh

.PHONY: publicar
publicar: ## Sobe fonte, código e script para o S3 do ministack e cria/atualiza o job Glue
	@test -d south-america/.git || { echo "rode 'make fonte' antes"; exit 1; }
	$(GLUE) publicar

.PHONY: executar
executar: ## Publica se algo mudou e executa bronze, silver, gold e a verificação; mostra o resumo
	@test -d south-america/.git || { echo "rode 'make fonte' antes"; exit 1; }
	$(GLUE) garantir
	$(GLUE) executar bronze,silver,gold,verificacao

.PHONY: verificar
verificar: ## Só os totais lidos das tabelas Iceberg, sem reprocessar
	$(GLUE) garantir
	$(GLUE) executar verificacao

.PHONY: e2e
e2e: ## Testes contra o ministack real (exige `make up` na raiz)
	$(UV) run pytest -m e2e
