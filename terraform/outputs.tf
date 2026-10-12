output "orchestrator_url" {
  description = "Public URL for Salamandra Orchestrator"
  value       = google_cloud_run_v2_service.agent_service["orchestrator"].uri
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository URI"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.a2a_repo.name}"
}

output "agent_urls" {
  description = "Cloud Run URIs for all Salamandra agents"
  value = {
    for k, v in google_cloud_run_v2_service.agent_service : k => v.uri
  }
}
