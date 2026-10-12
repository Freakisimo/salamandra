#!/usr/bin/env bash
set -e

# Salamandra Automated End-to-End Cloud Deployment Pipeline
# Usage: ./deploy.sh [PROJECT_ID] [REGION] [PREFIX]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Resolve Project ID
PROJECT_ID=${1:-${GCP_PROJECT_ID}}

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
fi

if [ -z "$PROJECT_ID" ] && [ -f "terraform/terraform.tfvars" ]; then
  PROJECT_ID=$(grep -E '^\s*project_id\s*=' terraform/terraform.tfvars | cut -d'=' -f2 | tr -d ' "' | tr -d "'")
fi

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: define PROJECT_ID (argumento, terraform/terraform.tfvars o gcloud config set project)"
  exit 1
fi

REGION=${2:-"us-central1"}
PREFIX=${3:-"salamandra"}

echo "=================================================="
echo "🚀 INICIANDO DESPLIEGUE CLOUD DE SALAMANDRA       "
echo "   Proyecto GCP: $PROJECT_ID"
echo "   Región:       $REGION"
echo "   Prefijo:      $PREFIX"
echo "=================================================="

# Actualizar variables en terraform.tfvars
cat <<EOF > terraform/terraform.tfvars
project_id = "$PROJECT_ID"
region     = "$REGION"
prefix     = "$PREFIX"
EOF

# 2. Habilitar APIs requeridas en GCP si no están activas
echo "[*] Verificando y habilitando APIs de GCP requeridas..."
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    iam.googleapis.com \
    --project="$PROJECT_ID" --quiet

# 3. Inicializar Terraform y aprovisionar Artifact Registry
cd terraform
if [ ! -d ".terraform" ]; then
  echo "[*] Fase 1: Inicializando Terraform..."
  terraform init
fi

echo "[*] Fase 2: Aprovisionando repositorio en Artifact Registry..."
terraform apply -target=google_artifact_registry_repository.a2a_repo -auto-approve
cd ..

# 4. Autenticar Docker con Artifact Registry
REPO_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${PREFIX}-a2a-agents"
echo "[*] Fase 3: Configurando autenticación Docker en ${REGION}-docker.pkg.dev..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# 5. Construir imagen Docker de Salamandra
echo "[*] Fase 4: Construyendo imagen Docker base de Salamandra..."
docker build -t salamandra-agent:latest .

# 6. Etiquetar y publicar imágenes para cada microservicio agente
AGENTS=("orchestrator" "fact-extractor" "gov-directory-scout" "corroborator" "source-analyst" "osint-analyst" "bias-analyst")

echo "[*] Fase 5: Publicando imágenes de los 7 agentes en Artifact Registry..."
for AGENT in "${AGENTS[@]}"; do
  TARGET_TAG="${REPO_URI}/${AGENT}:latest"
  echo "    -> Etiquetando y subiendo ${AGENT}..."
  docker tag salamandra-agent:latest "${TARGET_TAG}"
  docker push "${TARGET_TAG}"
done

# 7. Aplicar infraestructura completa en Cloud Run e IAM
echo "[*] Fase 6: Desplegando microservicios en Cloud Run con IAM A2A..."
cd terraform
terraform apply -auto-approve

echo "=================================================="
echo "✅ ¡Despliegue de Salamandra completado con éxito!"
echo "   URL del Orquestador:"
terraform output -raw orchestrator_url
echo ""
echo "=================================================="
cd ..
