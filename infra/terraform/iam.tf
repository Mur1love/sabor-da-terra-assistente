# Contas de serviço e IAM de menor privilégio.
#
# Uma identidade por papel; nenhuma usa a conta padrão do Compute e nenhuma
# recebe papel básico (owner/editor/viewer). Onde o recurso aceita IAM
# próprio (dataset, segredo, tópico, repositório, serviço do Cloud Run), o
# papel é concedido no recurso, não no projeto.

resource "google_service_account" "app" {
  account_id   = "sdt-app"
  display_name = "Sabor da Terra — interface (Cloud Run)"
  description  = "Identidade do Streamlit no Cloud Run: Gemini, BigQuery (leitura), Agent Search, Firestore e publicação de notificações."
}

resource "google_service_account" "funcoes" {
  account_id   = "sdt-funcoes"
  display_name = "Sabor da Terra — regras (Cloud Run functions)"
  description  = "Identidade das functions de extração, conformidade, urgência e alocação."
}

resource "google_service_account" "workflows" {
  account_id   = "sdt-workflows"
  display_name = "Sabor da Terra — fluxo da triagem (Workflows)"
  description  = "Chama as functions da triagem."
}

resource "google_service_account" "eventarc" {
  account_id   = "sdt-eventarc"
  display_name = "Sabor da Terra — gatilho Pub/Sub → Workflows"
  description  = "Inicia uma execução da triagem a cada pedido publicado."
}

resource "google_service_account" "deploy" {
  account_id   = "sdt-deploy"
  display_name = "Sabor da Terra — pipeline (Cloud Build)"
  description  = "Roda os testes, publica a imagem e faz o deploy no Cloud Run."
}

locals {
  # Papéis que só existem no nível do projeto (o recurso não tem IAM próprio).
  papeis_no_projeto = {
    "app-vertex"         = { sa = google_service_account.app.email, papel = "roles/aiplatform.user" }
    "app-bq-jobs"        = { sa = google_service_account.app.email, papel = "roles/bigquery.jobUser" }
    "app-busca"          = { sa = google_service_account.app.email, papel = "roles/discoveryengine.viewer" }
    "app-firestore"      = { sa = google_service_account.app.email, papel = "roles/datastore.user" }
    "app-logs"           = { sa = google_service_account.app.email, papel = "roles/logging.logWriter" }
    "funcoes-vertex"     = { sa = google_service_account.funcoes.email, papel = "roles/aiplatform.user" }
    "funcoes-bq-jobs"    = { sa = google_service_account.funcoes.email, papel = "roles/bigquery.jobUser" }
    "funcoes-logs"       = { sa = google_service_account.funcoes.email, papel = "roles/logging.logWriter" }
    "workflows-logs"     = { sa = google_service_account.workflows.email, papel = "roles/logging.logWriter" }
    "eventarc-receber"   = { sa = google_service_account.eventarc.email, papel = "roles/eventarc.eventReceiver" }
    "eventarc-workflows" = { sa = google_service_account.eventarc.email, papel = "roles/workflows.invoker" }
    "deploy-run"         = { sa = google_service_account.deploy.email, papel = "roles/run.developer" }
    "deploy-logs"        = { sa = google_service_account.deploy.email, papel = "roles/logging.logWriter" }
  }
}

resource "google_project_iam_member" "papeis" {
  for_each = local.papeis_no_projeto

  project = var.project_id
  role    = each.value.papel
  member  = "serviceAccount:${each.value.sa}"
}

# O pipeline faz o deploy "como" a conta do app, sem poder agir como as outras.
resource "google_service_account_iam_member" "deploy_usa_app" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}
