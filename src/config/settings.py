import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # GCP / Vertex AI
    GOOGLE_GENAI_USE_VERTEXAI: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "bisne-scout")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    A2A_PREFIX: str = os.getenv("A2A_PREFIX", "salamandra")

    # Local Ports
    ORCHESTRATOR_PORT: int = int(os.getenv("ORCHESTRATOR_PORT", "8000"))
    FACT_EXTRACTOR_PORT: int = int(os.getenv("FACT_EXTRACTOR_PORT", "8001"))
    CORROBORATOR_PORT: int = int(os.getenv("CORROBORATOR_PORT", "8002"))
    SOURCE_ANALYST_PORT: int = int(os.getenv("SOURCE_ANALYST_PORT", "8003"))
    OSINT_ANALYST_PORT: int = int(os.getenv("OSINT_ANALYST_PORT", "8004"))
    BIAS_ANALYST_PORT: int = int(os.getenv("BIAS_ANALYST_PORT", "8005"))
    GOV_DIRECTORY_SCOUT_PORT: int = int(os.getenv("GOV_DIRECTORY_SCOUT_PORT", "8006"))

    # Storage Paths
    DATA_DIR: Path = BASE_DIR / os.getenv("SALAMANDRA_DATA_DIR", "data")
    DB_NAME: str = os.getenv("SALAMANDRA_DB_NAME", "salamandra_directory.db")
    LEDGER_FILE: str = os.getenv("SALAMANDRA_LEDGER_FILE", "audit_ledger.jsonl")

    @property
    def DB_PATH(self) -> Path:
        return self.DATA_DIR / self.DB_NAME

    @property
    def LEDGER_PATH(self) -> Path:
        return self.DATA_DIR / self.LEDGER_FILE

    # Network / Timeout
    A2A_TIMEOUT_SECONDS: int = int(os.getenv("A2A_TIMEOUT_SECONDS", "180"))

    model_config = {"env_file": ".env", "extra": "allow"}

settings = Settings()
# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
