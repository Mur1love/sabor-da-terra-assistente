# Nenhuma variável traz valor real: project_id e region chegam por
# terraform.tfvars (fora do git, ver terraform.tfvars.example) ou -var.

variable "project_id" {
  description = "ID do projeto Google Cloud onde a cooperativa roda."
  type        = string
}

variable "region" {
  description = "Região dos serviços regionais (Cloud Run, functions, Workflows, BigQuery, Firestore, Scheduler)."
  type        = string
}

variable "local_vertex" {
  description = "Localização do Vertex AI para o Gemini (GOOGLE_CLOUD_LOCATION). Os modelos mais novos costumam sair primeiro no endpoint global."
  type        = string
  default     = "global"
}

variable "local_busca" {
  description = "Localização do data store do Agent Search (antigo Vertex AI Search): global, us ou eu."
  type        = string
  default     = "global"
}

variable "imagem_app" {
  description = "Imagem do app no Artifact Registry. Vazio = <região>-docker.pkg.dev/<projeto>/sabor-da-terra/app:latest; o Cloud Build troca pela tag do build a cada deploy."
  type        = string
  default     = ""
}

variable "objeto_codigo_funcoes" {
  description = "Objeto .zip no bucket de código com o pacote sabor_da_terra e os pontos de entrada HTTP das functions."
  type        = string
  default     = "funcoes/sabor_da_terra.zip"
}

variable "membros_equipe" {
  description = "Quem pode abrir a interface pelo IAP (ex.: group:equipe@dominio). Não há acesso público."
  type        = list(string)
  default     = []
}

variable "fuso_horario" {
  description = "Fuso dos agendamentos do Cloud Scheduler."
  type        = string
  default     = "America/Fortaleza"
}

variable "modelo_triagem" {
  description = "Modelo Gemini do papel TRIAGEM (classificação e extração)."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "modelo_resposta" {
  description = "Modelo Gemini do papel RESPOSTA (composição conversacional)."
  type        = string
  default     = "gemini-3.8-flash"
}
