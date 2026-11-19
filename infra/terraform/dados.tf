# Dados: BigQuery (estruturados), Cloud Storage (documentos do RAG),
# Agent Search (busca com citação), Firestore (sessão) e Secret Manager.

# ---------------------------------------------------------------- BigQuery --

locals {
  # Uma tabela por arquivo de infra/bigquery/ — gerados do esquema.py da
  # camada de dados (scripts/gerar_esquemas_bigquery.py), então o Terraform
  # e o código nunca divergem sobre colunas e tipos.
  pasta_esquemas = "${path.module}/../bigquery"
  tabelas        = toset([for arquivo in fileset(local.pasta_esquemas, "*.json") : trimsuffix(arquivo, ".json")])
}

resource "google_bigquery_dataset" "cooperativa" {
  dataset_id  = "sabor_da_terra"
  location    = var.region
  description = "Dados estruturados da cooperativa (docs/04 §2): o assistente consulta por funções, nunca pelo prompt."
  labels      = local.rotulos

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_table" "tabelas" {
  for_each = local.tabelas

  dataset_id  = google_bigquery_dataset.cooperativa.dataset_id
  table_id    = each.key
  schema      = file("${local.pasta_esquemas}/${each.key}.json")
  description = "Esquema igual ao de sabor_da_terra/dados/esquema.py (tabela ${each.key})."
  labels      = local.rotulos
}

# Leitura só neste dataset: as ferramentas não escrevem dado da cooperativa.
resource "google_bigquery_dataset_iam_member" "leitores" {
  for_each = {
    app     = google_service_account.app.email
    funcoes = google_service_account.funcoes.email
  }

  dataset_id = google_bigquery_dataset.cooperativa.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${each.value}"
}

# ----------------------------------------------------------- Cloud Storage --

resource "google_storage_bucket" "documentos" {
  name                        = "${var.project_id}-documentos"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = local.rotulos

  # Certificação e contrato têm validade: a versão antiga é evidência.
  versioning {
    enabled = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "codigo_funcoes" {
  name                        = "${var.project_id}-codigo-funcoes"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = local.rotulos

  depends_on = [google_project_service.apis]
}

# ------------------------------------------- Agent Search (Vertex AI Search) --

resource "google_discovery_engine_data_store" "documentos" {
  location          = var.local_busca
  data_store_id     = "sabor-da-terra-documentos"
  display_name      = "Sabor da Terra — certificações, contratos e fichas"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]

  depends_on = [google_project_service.apis]
}

# A importação dos documentos (gs://<projeto>-documentos → data store) roda
# com o agente de serviço do Discovery Engine, que só lê este bucket.
resource "google_storage_bucket_iam_member" "busca_le_documentos" {
  bucket = google_storage_bucket.documentos.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${data.google_project.atual.number}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
}

# --------------------------------------------------------------- Firestore --

resource "google_firestore_database" "sessoes" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------- Secret Manager --

# Chave do AI Studio como plano B do Vertex AI (docs/04 §4). Só o contêiner do
# segredo: o valor entra fora do Terraform (o estado não guarda chave) com
# `gcloud secrets versions add gemini-api-key`. Para usar, troque
# GOOGLE_GENAI_USE_VERTEXAI para FALSE e monte o segredo como GEMINI_API_KEY.
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  labels    = local.rotulos

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "app_le_chave" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}
