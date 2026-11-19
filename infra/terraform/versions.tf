# Versões validadas com `terraform validate` em 18/11/2026 (Terraform 1.17.2,
# provider google 8.12.0). Nada aqui foi aplicado: o protótipo roda local
# (princípio 2 do docs/03); este diretório é o desenho de produção em código.

terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.12"
    }
  }

  # Estado remoto num bucket do próprio projeto, criado antes do primeiro
  # apply. Fica comentado porque `terraform init` com backend gcs exige
  # credenciais, e a validação local roda sem nenhuma.
  # backend "gcs" {
  #   bucket = "<BUCKET_DO_ESTADO>"
  #   prefix = "sabor-da-terra"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
