terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  agents = toset([
    "orchestrator",
    "fact-extractor",
    "gov-directory-scout",
    "corroborator",
    "source-analyst",
    "osint-analyst",
    "bias-analyst"
  ])
  workers = toset([
    "fact-extractor",
    "gov-directory-scout",
    "corroborator",
    "source-analyst",
    "osint-analyst",
    "bias-analyst"
  ])
}

# 1. Enable Required GCP APIs
resource "google_project_service" "vertex_ai" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "a2a_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.prefix}-a2a-agents"
  description   = "Artifact Registry for Salamandra A2A Agent Containers"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}

# 3. Dedicated Service Account per Agent
resource "google_service_account" "agent_sa" {
  for_each = local.agents

  project      = var.project_id
  account_id   = "${var.prefix}-${each.key}-sa"
  display_name = "Service Account for Salamandra Agent: ${each.key}"
}

# 4. Cloud Run v2 Services per Agent
resource "google_cloud_run_v2_service" "agent_service" {
  for_each = local.agents

  project             = var.project_id
  location            = var.region
  name                = "${var.prefix}-${each.key}"
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.agent_sa[each.key].email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.prefix}-a2a-agents/${each.key}:latest"

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
        name  = "A2A_AGENT_NAME"
        value = each.key
      }

      env {
        name  = "AGENT_FILE"
        value = "src/agents/${replace(each.key, "-", "_")}.py"
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      env {
        name  = "PYTHONPATH"
        value = "/app"
      }

      env {
        name  = "A2A_PREFIX"
        value = var.prefix
      }
    }
  }

  labels = {
    managed_by = "terraform"
    project    = "salamandra"
    protocol   = "agent-to-agent"
  }

  depends_on = [google_project_service.cloud_run]
}

# 5. Public Access for Orchestrator (Entrypoint)
resource "google_cloud_run_v2_service_iam_member" "public_orchestrator" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agent_service["orchestrator"].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 6. IAM Invocation: Orchestrator Service Account can invoke Worker Cloud Run Services
resource "google_cloud_run_v2_service_iam_member" "orchestrator_invokes_workers" {
  for_each = local.workers

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agent_service[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.agent_sa["orchestrator"].email}"
}

# 7. Grant Vertex AI User permissions to all Agent Service Accounts
resource "google_project_iam_member" "vertex_ai_user" {
  for_each = local.agents

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa[each.key].email}"
}

# 8. Grant Cloud Run Viewer permission to Orchestrator SA to discover worker agent Cloud Run URLs
resource "google_project_iam_member" "orchestrator_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.agent_sa["orchestrator"].email}"
}
