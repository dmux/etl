#!/usr/bin/env bash
# Publica e executa o job AWS Glue `futebol-pipeline` no ministack, com o AWS CLI (ADR-009).
#
#   scripts/glue.sh publicar                 fonte, código e script no S3; cria ou atualiza o job
#   scripts/glue.sh garantir                 publica só se algo mudou desde a última publicação
#   scripts/glue.sh executar <camadas>       executa, espera, resume e decide pelo marcador do log
#
# A saída de `executar` é um resumo em tabela; o log filtrado da execução fica em
# dist/ultima-execucao.log. Os comandos /glue:executar e /glue:verificar leem os dois.
#
# O resultado vem da linha `etl_futebol: codigo_saida=N` no log, não do JobRunState: a imagem
# Glue do ministack pode marcar SUCCEEDED um job que falhou (convencoes-spark.md).
set -euo pipefail

cd "$(dirname "$0")/.."

ENDPOINT="${MINISTACK_ENDPOINT:-http://localhost:4566}"
BUCKET="futebol-lake"
JOB="futebol-pipeline"
LOG_GROUP="/aws-glue/jobs/output"
LOG_STREAM="spark-stdout-stream"
ESPERA_MAXIMA_S="${ESPERA_MAXIMA_S:-1800}"

export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

aws_ministack() { aws --endpoint-url "$ENDPOINT" "$@"; }

# Iceberg 1.0 da imagem Glue 4.0: jars na frente do classpath (o AWS SDK v2 2.29 da imagem colide
# com o bundle 2.17 do Iceberg) e catálogo `hadoop` no S3 (o GlueCatalog 1.0 não aceita endpoint).
conf_iceberg() {
  local jars=/home/glue_user/aws-glue-libs/datalake-connectors/iceberg-1.0.0
  local classpath="$jars/iceberg-spark-runtime-3.3_2.12-1.0.0.jar:$jars/bundle-2.17.161.jar"
  classpath+=":$jars/url-connection-client-2.17.161.jar:/home/glue_user/spark/jars/*:/home/glue_user/aws-glue-libs/jars/*"
  local catalogo=spark.sql.catalog.iceberg
  printf '%s' "spark.driver.extraClassPath=$classpath" \
    " --conf spark.executor.extraClassPath=$classpath" \
    " --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions" \
    " --conf $catalogo=org.apache.iceberg.spark.SparkCatalog" \
    " --conf $catalogo.type=hadoop" \
    " --conf $catalogo.warehouse=s3a://$BUCKET/warehouse"
}

definicao_do_job() {
  jq -n \
    --arg script "s3://$BUCKET/scripts/glue_job.py" \
    --arg codigo "s3a://$BUCKET/codigo/etl_futebol.zip" \
    --arg conf "$(conf_iceberg)" \
    --arg fonte "s3a://$BUCKET/fonte" \
    --arg warehouse "s3a://$BUCKET/warehouse" \
    '{Role: "arn:aws:iam::000000000000:role/glue", GlueVersion: "4.0", Timeout: 60,
      Command: {Name: "glueetl", ScriptLocation: $script, PythonVersion: "3"},
      DefaultArguments: {"--extra-py-files": $codigo, "--conf": $conf, "--fonte": $fonte,
                         "--warehouse": $warehouse, "--camadas": "bronze,silver,gold"}}'
}

# Impressão digital do que vai para o ministack: código, script, definição do job e commit da fonte.
impressao_local() {
  {
    find src -name '*.py' -not -path '*__pycache__*' | sort | xargs shasum
    shasum glue_job.py
    definicao_do_job
    git -C south-america rev-parse HEAD
  } | shasum | cut -d' ' -f1
}

impressao_publicada() {
  aws_ministack s3 cp --quiet "s3://$BUCKET/codigo/impressao.txt" - 2>/dev/null || true
}

garantir() {
  if aws_ministack glue get-job --job-name "$JOB" >/dev/null 2>&1 && [ "$(impressao_publicada)" = "$(impressao_local)" ]; then
    echo "publicação em dia: job $JOB, código e fonte iguais aos do ministack"
    return 0
  fi
  echo "algo mudou desde a última publicação (ou o ministack foi reiniciado): publicando"
  publicar
}

publicar() {
  aws_ministack s3 mb "s3://$BUCKET" >/dev/null 2>&1 || true
  aws_ministack s3 sync --quiet --delete south-america/ "s3://$BUCKET/fonte/" --exclude ".git/*" --exclude "*" --include "*.txt"
  echo "fonte: $(aws_ministack s3 ls "s3://$BUCKET/fonte/" --recursive | wc -l | tr -d ' ') arquivos em s3://$BUCKET/fonte/"
  mkdir -p dist && rm -f dist/etl_futebol.zip
  (cd src && zip -qr ../dist/etl_futebol.zip etl_futebol -x '*__pycache__*')
  aws_ministack s3 cp --quiet dist/etl_futebol.zip "s3://$BUCKET/codigo/etl_futebol.zip"
  aws_ministack s3 cp --quiet glue_job.py "s3://$BUCKET/scripts/glue_job.py"
  local definicao
  definicao="$(definicao_do_job)"
  if aws_ministack glue get-job --job-name "$JOB" >/dev/null 2>&1; then
    aws_ministack glue update-job --job-name "$JOB" --job-update "$definicao" >/dev/null
    echo "job $JOB atualizado"
  else
    aws_ministack glue create-job --name "$JOB" --cli-input-json "$(jq '. + {Name: "'"$JOB"'"}' <<<"$definicao")" >/dev/null
    echo "job $JOB criado"
  fi
  impressao_local | aws_ministack s3 cp --quiet - "s3://$BUCKET/codigo/impressao.txt"
}

# Todas as mensagens do stream, na ordem, seguindo a paginação do CloudWatch Logs.
ler_log() {
  local token="" anterior="" pagina
  while :; do
    if [ -n "$token" ]; then
      pagina="$(aws_ministack logs get-log-events --log-group-name "$LOG_GROUP" --log-stream-name "$LOG_STREAM" --start-from-head --next-token "$token")"
    else
      pagina="$(aws_ministack logs get-log-events --log-group-name "$LOG_GROUP" --log-stream-name "$LOG_STREAM" --start-from-head)"
    fi
    jq -r '.events[].message' <<<"$pagina"
    anterior="$token"
    token="$(jq -r '.nextForwardToken // empty' <<<"$pagina")"
    if [ -z "$token" ] || [ "$token" = "$anterior" ]; then
      break
    fi
  done
}

esperar() {
  local execucao="$1" estado inicio=$SECONDS
  while :; do
    estado="$(aws_ministack glue get-job-run --job-name "$JOB" --run-id "$execucao" --query JobRun.JobRunState --output text)"
    case "$estado" in SUCCEEDED | FAILED | STOPPED | ERROR | TIMEOUT) break ;; esac
    if [ $((SECONDS - inicio)) -gt "$ESPERA_MAXIMA_S" ]; then
      echo "execução $execucao não terminou em ${ESPERA_MAXIMA_S}s" >&2
      return 1
    fi
    sleep 10
  done
  echo "JobRunState=$estado em $((SECONDS - inicio))s (informativo: o resultado vem do marcador)"
}

# Resumo em markdown a partir do log: uma linha por camada, os totais da verificação e as falhas.
resumir() {
  awk '
    /relatório da camada [a-z]+:/ { match($0, /camada [a-z]+/); camada = substr($0, RSTART + 7, RLENGTH - 7); next }
    camada != "" && /^[^ ]+  (ok|falhou|nao_carregado)  declarado=/ {
      split($0, campos, "  "); situacao[camada, campos[2]]++
      if (campos[2] == "falhou") falhas[++n] = $0
      next
    }
    camada != "" && /^total: / {
      match($0, /gravadas=[0-9]+/); gravadas = substr($0, RSTART + 9, RLENGTH - 9)
      match($0, /rejeitadas=[0-9]+/); rejeitadas = substr($0, RSTART + 11, RLENGTH - 11)
      linhas[++c] = sprintf("| %s | %d | %d | %d | %s | %s |", camada, situacao[camada, "ok"], situacao[camada, "falhou"], situacao[camada, "nao_carregado"], gravadas, rejeitadas)
      camada = ""; next
    }
    /etl_futebol: verificacao [a-z0-9_]+=[0-9]+/ {
      match($0, /verificacao [a-z0-9_]+=[0-9]+/); split(substr($0, RSTART + 12, RLENGTH - 12), par, "=")
      totais[++t] = sprintf("| %s | %s |", par[1], par[2]); next
    }
    END {
      if (c > 0) {
        print "| camada | ok | falhou | nao_carregado | gravadas | rejeitadas |"
        print "| --- | --- | --- | --- | --- | --- |"
        for (i = 1; i <= c; i++) print linhas[i]
        print ""
      }
      if (t > 0) {
        print "| verificação | valor |"
        print "| --- | --- |"
        for (i = 1; i <= t; i++) print totais[i]
        print ""
      }
      for (i = 1; i <= n; i++) print "falhou: " falhas[i]
    }
  '
}

executar() {
  local camadas="${1:?informe as camadas, ex.: bronze,silver,gold}" execucao log marcador
  # Um único stream para todas as execuções: limpo antes, para ler só esta.
  aws_ministack logs delete-log-stream --log-group-name "$LOG_GROUP" --log-stream-name "$LOG_STREAM" >/dev/null 2>&1 || true
  execucao="$(aws_ministack glue start-job-run --job-name "$JOB" --arguments "$(jq -n --arg c "$camadas" '{"--camadas": $c}')" --query JobRunId --output text)"
  echo "execução $execucao ($camadas)"
  esperar "$execucao"
  log="$(ler_log)"
  mkdir -p dist
  # Sem o ruído do Spark (log4j, SLF4J e pilhas Java): sobram o log do pipeline e eventuais tracebacks.
  grep -v -E '^[0-9]{2}/[0-9]{2}/[0-9]{2} [0-9:]{8} |^[[:space:]]+at |^\[log-forwarder\]|^SLF4J|^Output:|^$' <<<"$log" >dist/ultima-execucao.log || true
  echo "log filtrado: dist/ultima-execucao.log ($(wc -l <dist/ultima-execucao.log | tr -d ' ') linhas)"
  echo
  resumir <dist/ultima-execucao.log
  marcador="$(grep -o 'etl_futebol: codigo_saida=[0-9]*' <<<"$log" | tail -1 || true)"
  if [ "$marcador" = "etl_futebol: codigo_saida=0" ]; then
    echo "RESULTADO: sucesso"
    return 0
  fi
  if grep -q "Traceback" dist/ultima-execucao.log; then
    echo "--- traceback ---"
    sed -n '/Traceback (most recent call last)/,$p' dist/ultima-execucao.log | head -40
  fi
  echo "RESULTADO: falha (${marcador:-sem marcador no log — o job não chegou ao fim})" >&2
  return 1
}

case "${1:-}" in
  publicar) publicar ;;
  garantir) garantir ;;
  executar) executar "${2:-}" ;;
  *)
    echo "uso: $0 publicar | garantir | executar <camadas>" >&2
    exit 2
    ;;
esac
