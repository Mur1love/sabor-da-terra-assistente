# Container do assistente Sabor da Terra (etapa 15, issue #15).
#
# Destino no desenho: Cloud Run, com a imagem guardada no Artifact Registry
# (infra/terraform/run.tf). O Cloud Run injeta a porta em $PORT (8080 por
# padrão); o Streamlit escuta nela. Build e teste local:
#
#   docker build -t sabor-da-terra .
#   docker run --rm -p 8080:8080 -e LLM_MODO=fixture sabor-da-terra
#
# Nenhum segredo entra na imagem: o .env fica de fora (.dockerignore) e, no
# Cloud Run, a configuração chega por variável de ambiente e Secret Manager.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# Dependências antes do código: mudar o código não refaz esta camada.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY sabor_da_terra/ sabor_da_terra/
COPY data/ data/
# A triagem lê os 15 pedidos estruturados e o modo fixture lê as respostas
# gravadas do LLM: os dois moram em tests/fixtures/.
COPY tests/fixtures/ tests/fixtures/

# Usuário sem privilégio; o índice do RAG é gravado em /app/.cache.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/.cache \
    && chown -R app:app /app/.cache
USER app

EXPOSE 8080

# sh -c para expandir $PORT; o exec deixa o Streamlit como PID 1 e ele recebe
# o SIGTERM que o Cloud Run manda ao desligar a instância.
CMD ["sh", "-c", "exec streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true --server.fileWatcherType=none --browser.gatherUsageStats=false"]
