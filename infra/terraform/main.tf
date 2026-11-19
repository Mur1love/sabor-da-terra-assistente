# APIs que o desenho usa (docs/04 §2 e §4) e valores derivados.

locals {
  rotulos = {
    sistema = "sabor-da-terra"
    etapa   = "15"
  }

  imagem_app = (
    var.imagem_app != ""
    ? var.imagem_app
    : "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}/app:latest"
  )

  apis = toset([
    "aiplatform.googleapis.com",       # Vertex AI (Gemini)
    "artifactregistry.googleapis.com", # imagens do app
    "bigquery.googleapis.com",         # dados estruturados
    "cloudbuild.googleapis.com",       # pipeline e build das functions
    "cloudfunctions.googleapis.com",   # Cloud Run functions (regras)
    "cloudscheduler.googleapis.com",   # disparos agendados
    "discoveryengine.googleapis.com",  # Agent Search (antigo Vertex AI Search)
    "eventarc.googleapis.com",         # Pub/Sub → Workflows
    "firestore.googleapis.com",        # sessão do assistente
    "iam.googleapis.com",              # contas de serviço
    "iap.googleapis.com",              # login na frente da UI
    "logging.googleapis.com",          # Cloud Logging
    "pubsub.googleapis.com",           # entrada de pedidos e notificações
    "run.googleapis.com",              # Cloud Run (UI + functions)
    "secretmanager.googleapis.com",    # chave da API
    "storage.googleapis.com",          # documentos do RAG
    "workflows.googleapis.com",        # fluxo da triagem
  ])
}

# Número do projeto, para nomear os agentes de serviço do Google (IAP, Agent Search).
data "google_project" "atual" {}

resource "google_project_service" "apis" {
  for_each = local.apis

  service            = each.value
  disable_on_destroy = false
}
