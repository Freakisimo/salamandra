variable "project_id" {
  description = "The GCP Project ID to deploy Salamandra agents"
  type        = string
}

variable "region" {
  description = "The GCP region for Cloud Run and Artifact Registry"
  type        = string
  default     = "us-central1"
}

variable "prefix" {
  description = "Resource prefix identifier for Salamandra A2A services"
  type        = string
  default     = "salamandra"
}
