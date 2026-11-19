# Interface conversacional: Streamlit no Cloud Run, imagem no Artifact Registry.

resource "google_artifact_registry_repository" "app" {
  repository_id = "sabor-da-terra"
  location      = var.region
  format        = "DOCKER"
  description   = "Imagens do assistente Sabor da Terra (Dockerfile na raiz do repositório)."
  labels        = local.rotulos

  depends_on = [google_project_service.apis]
}

resource "google_artifact_registry_repository_iam_member" "deploy_publica" {
  repository = google_artifact_registry_repository.app.name
  location   = google_artifact_registry_repository.app.location
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_cloud_run_v2_service" "app" {
  name     = "sabor-da-terra"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # o controle de acesso é o IAP, não a rede
  labels   = local.rotulos

  # Login Google na frente da UI (IAP nativo do Cloud Run). Só run.invoker não
  # basta: o navegador não manda o token de identidade que ele exige.
  iap_enabled = true

  template {
    service_account = google_service_account.app.email
    # O Streamlit mantém a conversa num websocket: a mesma pessoa precisa
    # voltar à mesma instância, e a conexão pode durar a sessão inteira.
    session_affinity = true
    timeout          = "3600s"

    scaling {
      min_instance_count = 0 # escala a zero fora do expediente (custo ~0)
      max_instance_count = 3
    }

    containers {
      image = local.imagem_app

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "LLM_MODO"
        value = "real"
      }
      # Em produção o Gemini vem do Vertex AI com a identidade da conta de
      # serviço (ADC), sem chave. A chave do AI Studio fica guardada no Secret
      # Manager como plano B (dados.tf), sem montar aqui: com as duas
      # configuradas, o SDK teria de escolher entre elas.
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.local_vertex
      }
      env {
        name  = "GEMINI_MODELO_TRIAGEM"
        value = var.modelo_triagem
      }
      env {
        name  = "GEMINI_MODELO_RESPOSTA"
        value = var.modelo_resposta
      }
      # Onde ficam os recursos que os adaptadores Google vão usar; o código
      # atual ainda lê data/ de dentro da imagem (docs/04 §11.4).
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.cooperativa.dataset_id
      }
      env {
        name  = "AGENT_SEARCH_DATA_STORE"
        value = google_discovery_engine_data_store.documentos.data_store_id
      }
      env {
        name  = "TOPICO_NOTIFICACOES"
        value = google_pubsub_topic.notificacoes.name
      }

      startup_probe {
        http_get {
          path = "/_stcore/health"
        }
      }
    }
  }

  lifecycle {
    # A imagem muda a cada deploy do Cloud Build (tag do build); o Terraform
    # cuida do resto do serviço e não desfaz o deploy.
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [google_project_service.apis]
}

# O IAP chama o serviço em nome de quem fez login.
resource "google_cloud_run_v2_service_iam_member" "iap_invoca" {
  name     = google_cloud_run_v2_service.app.name
  location = google_cloud_run_v2_service.app.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.atual.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# Quem da equipe passa pelo IAP. Nada de acesso público: a UI mostra dado de produtor.
resource "google_iap_web_cloud_run_service_iam_member" "equipe" {
  for_each = toset(var.membros_equipe)

  cloud_run_service_name = google_cloud_run_v2_service.app.name
  location               = google_cloud_run_v2_service.app.location
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = each.value
}
