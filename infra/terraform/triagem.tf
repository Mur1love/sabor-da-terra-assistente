# Triagem em produção: Cloud Run functions com as regras, Workflows
# orquestrando (infra/workflows/triagem.yaml), Pub/Sub + Eventarc como entrada
# de pedidos e Cloud Scheduler para os disparos periódicos aos produtores.

locals {
  # Uma function por passo do fluxo. As regras da #5 ficam juntas em
  # validar-item: a primeira fase delas é encadeada (cada regra só olha os
  # produtores que as anteriores não excluíram), e separar uma function por
  # regra obrigaria a serializar o contexto inteiro entre chamadas HTTP.
  funcoes = {
    "extrair-pedido" = {
      entrada   = "extrair_pedido"
      descricao = "Etapa 9: classificação e extração estruturada com Gemini Flash-Lite (triagem/extrair.py)."
      memoria   = "512Mi"
      timeout   = 120
      variavel  = "URL_EXTRAIR_PEDIDO"
    }
    "validar-item" = {
      entrada   = "validar_item"
      descricao = "Etapa 5: regras de conformidade de um item (regras/conformidade.py, verificar_conformidade)."
      memoria   = "512Mi"
      timeout   = 60
      variavel  = "URL_VALIDAR_ITEM"
    }
    "classificar-urgencia" = {
      entrada   = "classificar_urgencia"
      descricao = "Etapa 10: urgência por horas até o prazo, contrato e sinais do texto (triagem/priorizar.py)."
      memoria   = "256Mi"
      timeout   = 60
      variavel  = "URL_CLASSIFICAR_URGENCIA"
    }
    "alocar-semana" = {
      entrada   = "alocar_semana"
      descricao = "Etapa 10: sugestão de alocação dentro da capacidade semanal (triagem/alocar.py)."
      memoria   = "512Mi"
      timeout   = 60
      variavel  = "URL_ALOCAR_SEMANA"
    }
  }
}

resource "google_cloudfunctions2_function" "triagem" {
  for_each = local.funcoes

  name        = each.key
  location    = var.region
  description = each.value.descricao
  labels      = local.rotulos

  build_config {
    runtime     = "python311"
    entry_point = each.value.entrada
    source {
      storage_source {
        bucket = google_storage_bucket.codigo_funcoes.name
        object = var.objeto_codigo_funcoes
      }
    }
  }

  service_config {
    service_account_email = google_service_account.funcoes.email
    # Só o Workflows (tráfego interno do Google Cloud) chama as functions.
    ingress_settings               = "ALLOW_INTERNAL_ONLY"
    all_traffic_on_latest_revision = true
    available_memory               = each.value.memoria
    timeout_seconds                = each.value.timeout
    min_instance_count             = 0
    max_instance_count             = 5

    environment_variables = {
      LLM_MODO                  = "real"
      GOOGLE_GENAI_USE_VERTEXAI = "TRUE"
      GOOGLE_CLOUD_PROJECT      = var.project_id
      GOOGLE_CLOUD_LOCATION     = var.local_vertex
      GEMINI_MODELO_TRIAGEM     = var.modelo_triagem
    }
  }

  depends_on = [google_project_service.apis]
}

# O Workflows invoca cada function com OIDC; ninguém mais pode.
resource "google_cloud_run_v2_service_iam_member" "workflows_invoca" {
  for_each = google_cloudfunctions2_function.triagem

  name     = each.value.name
  location = each.value.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.workflows.email}"
}

resource "google_workflows_workflow" "triagem" {
  name            = "triagem-pedidos"
  region          = var.region
  description     = "Extração → validações → urgência → alocação de um pedido (espelha triagem/fila.py)."
  service_account = google_service_account.workflows.id
  source_contents = file("${path.module}/../workflows/triagem.yaml")
  call_log_level  = "LOG_ERRORS_ONLY"
  labels          = local.rotulos

  user_env_vars = {
    for nome, funcao in local.funcoes :
    funcao.variavel => google_cloudfunctions2_function.triagem[nome].service_config[0].uri
  }

  depends_on = [google_project_service.apis]
}

# ----------------------------------------------------------------- Pub/Sub --

# Canais de entrada (e-mail, formulário, WhatsApp) publicam um pedido aqui.
resource "google_pubsub_topic" "pedidos" {
  name                       = "pedidos-entrada"
  labels                     = local.rotulos
  message_retention_duration = "604800s" # 7 dias para reprocessar

  depends_on = [google_project_service.apis]
}

# Pedido de resumo/notificação ao produtor (UI e Scheduler).
resource "google_pubsub_topic" "notificacoes" {
  name   = "notificacoes-produtores"
  labels = local.rotulos

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic_iam_member" "app_publica_notificacao" {
  topic  = google_pubsub_topic.notificacoes.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.app.email}"
}

# Cada pedido publicado vira uma execução do workflow da triagem.
resource "google_eventarc_trigger" "pedido_recebido" {
  name            = "pedido-recebido"
  location        = var.region
  service_account = google_service_account.eventarc.email
  labels          = local.rotulos

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.pubsub.topic.v1.messagePublished"
  }

  transport {
    pubsub {
      topic = google_pubsub_topic.pedidos.id
    }
  }

  destination {
    workflow = google_workflows_workflow.triagem.id
  }

  depends_on = [google_project_service.apis]
}

# --------------------------------------------------------- Cloud Scheduler --

locals {
  agendamentos = {
    "resumo-mensal-produtores" = {
      cron      = "0 8 1 * *" # dia 1 de cada mês, 8h
      descricao = "Resumo do mês para cada produtor (produtores/resumo_produtor)."
      tipo      = "resumo_mensal"
    }
    "pendencias-vencidas" = {
      cron      = "0 8 * * 1" # segunda-feira, 8h
      descricao = "Relatório semanal de pagamentos vencidos (produtores/relatorio_pendencias_vencidas)."
      tipo      = "pendencias_vencidas"
    }
  }
}

resource "google_cloud_scheduler_job" "produtores" {
  for_each = local.agendamentos

  name        = each.key
  region      = var.region
  description = each.value.descricao
  schedule    = each.value.cron
  time_zone   = var.fuso_horario

  pubsub_target {
    topic_name = google_pubsub_topic.notificacoes.id
    data       = base64encode(jsonencode({ tipo = each.value.tipo }))
  }

  depends_on = [google_project_service.apis]
}
