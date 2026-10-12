import os
import re
import uuid
import requests
from typing import Optional, Dict, Any
from src.config.settings import settings

def get_id_token(target_url: str) -> Optional[str]:
    """Retrieves GCP OIDC ID token for Cloud Run IAM invocation if available."""
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token
        auth_req = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(auth_req, target_url)
    except Exception:
        return None

def get_cloud_run_service_url(agent_name: str) -> Optional[str]:
    """Dynamically queries GCP Cloud Run API v2 to get target agent URI if in GCP."""
    project_id = settings.GOOGLE_CLOUD_PROJECT
    region = settings.GOOGLE_CLOUD_LOCATION
    prefix = settings.A2A_PREFIX

    if not project_id:
        return None

    try:
        import google.auth
        import google.auth.transport.requests
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.before_request(auth_req, "GET", "https://run.googleapis.com", {})

        kebab_name = re.sub(r'(?<!^)(?=[A-Z])', '-', agent_name).lower().replace("_", "-")
        service_name = f"{prefix}-{kebab_name}"

        api_url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/services/{service_name}"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        res = requests.get(api_url, headers=headers, timeout=4)
        if res.status_code == 200:
            return res.json().get("uri")
    except Exception:
        pass
    return None

def extract_text_from_a2a_response(data: Any) -> str:
    """
    Extrae de forma robusta y segura el contenido textual de una respuesta A2A JSON-RPC 2.0.
    Maneja esquemas V0.3 y V1.0 de A2A, artefactos, historiales (ROLE_AGENT / agent / assistant),
    mensajes de estado y objetos de error sin lanzar excepciones.
    """
    if not isinstance(data, dict):
        return str(data)

    # 1. Error de protocolo o ejecución
    if "error" in data:
        err = data["error"]
        if isinstance(err, dict):
            msg = err.get("message", "Error interno")
            code = err.get("code", "N/A")
            detail = err.get("data")
            return f"Error en agente A2A (código {code}): {msg}" + (f" - Detalle: {detail}" if detail else "")
        return f"Error en agente A2A: {err}"

    res = data.get("result")
    if not isinstance(res, dict):
        return str(data)

    # 2. Revisar Artifacts (si el agente generó un artefacto principal)
    artifacts = res.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        for art in reversed(artifacts):
            if isinstance(art, dict):
                parts = art.get("parts")
                if isinstance(parts, list) and parts:
                    for p in parts:
                        if isinstance(p, dict) and p.get("text"):
                            return p["text"]
                        elif isinstance(p, str):
                            return p

    # 3. Revisar Historial (mensajes con role 'agent', 'ROLE_AGENT' o 'assistant')
    history = res.get("history")
    if isinstance(history, list) and history:
        for item in reversed(history):
            if isinstance(item, dict):
                role = str(item.get("role", "")).upper()
                if "AGENT" in role or "ASSISTANT" in role or "MODEL" in role:
                    parts = item.get("parts")
                    if isinstance(parts, list):
                        text_parts = []
                        for part in parts:
                            if isinstance(part, dict) and part.get("text"):
                                text_parts.append(part["text"])
                            elif isinstance(part, str):
                                text_parts.append(part)
                        if text_parts:
                            return "\n\n".join(text_parts)

    # 4. Revisar status.message
    status = res.get("status")
    if isinstance(status, dict):
        msg = status.get("message")
        if isinstance(msg, dict):
            parts = msg.get("parts")
            if isinstance(parts, list) and parts:
                text_parts = []
                for p in parts:
                    if isinstance(p, dict) and p.get("text"):
                        text_parts.append(p["text"])
                    elif isinstance(p, str):
                        text_parts.append(p)
                if text_parts:
                    return "\n\n".join(text_parts)

    # 5. Si no se halló texto formateado, devolver representación legible
    return str(res)

def call_a2a_agent(agent_name: str, task: str, target_url: Optional[str] = None) -> str:
    """
    Sends a task to an autonomous Google ADK agent using the A2A JSON-RPC 2.0 protocol.
    
    Args:
        agent_name: The name of the registered target agent.
        task: The prompt or instruction text.
        target_url: Explicit URL override (optional).
        
    Returns:
        The text response generated by the agent.
    """
    # 1. Check direct env override
    if not target_url:
        env_keys = [
            f"A2A_TARGET_{agent_name.upper()}_URL",
            f"A2A_TARGET_{agent_name.lower()}_URL",
            f"A2A_TARGET_{agent_name}_URL"
        ]
        for key in env_keys:
            val = os.getenv(key)
            if val:
                target_url = val
                break

    # 2. Check Cloud Run URL
    if not target_url:
        target_url = get_cloud_run_service_url(agent_name)

    # 3. Check local port registry fallback
    if not target_url:
        from src.core.registry import registry
        agent_info = registry.get_agent(agent_name)
        if agent_info:
            target_url = f"http://localhost:{agent_info.port}"
        else:
            return f"Error: Agente '{agent_name}' no se encuentra en el registro de Salamandra."

    url = target_url.rstrip("/") + "/"
    headers = {"Content-Type": "application/json"}

    if target_url.startswith("https://"):
        token = get_id_token(target_url)
        if token:
            headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": "1",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": task}]
            }
        }
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.A2A_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        return extract_text_from_a2a_response(data)
    except Exception as e:
        return f"Error al comunicar con agente '{agent_name}' en {url}: {str(e)}"
