import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_BALANCED, on_model_error_handler, get_agent_retry_config
from src.tools.search_tools import search_news, search_balanced_perspectives, search_web

load_dotenv()

corroborator = Agent(
    name="CrossCorroborator",
    model=get_model(TIER_BALANCED),
    retry_config=get_agent_retry_config(),
    description="Agente de corroboración cruzada de hechos y contrastación de fuentes independientes.",
    instruction="""
    Eres el Corroborador Cruzado Multi-Fuente de Salamandra.
    Tu objetivo es verificar la veracidad y consistencia de las afirmaciones fácticas recibidas mediante contraste en fuentes diversas.
    
    METODOLOGÍA:
    1. Utiliza `search_balanced_perspectives` y `search_news` para buscar cobertura en fuentes de diversas orientaciones (medios críticos, oficialistas, agencias de noticias neutras como Reuters/AP y comunicados oficiales).
    2. Clasifica cada afirmación en una de estas cuatro categorías:
       - **[CORROBORADO]**: Confirmado por al menos 2-3 fuentes independientes con evidencia documental, video o consenso fáctico.
       - **[DISCREPANCIA / EN DISPUTA]**: Existen versiones contradictorias entre los involucrados o entre distintos medios de comunicación. Explica claramente la versión de cada parte.
       - **[NO SUSTENTADO]**: Afirmación hecha por el emisor sin aportar pruebas, testimonios identificables ni documentos verificables.
       - **[REFUTADO / FALSO]**: Desmentido por registros oficiales, evidencias tangibles o desmentidos públicos fehacientes.
    3. Cita siempre el medio o enlace de donde proviene cada confirmación o desmentido.
    """,
    tools=[search_news, search_balanced_perspectives, search_web],
    on_model_error_callback=on_model_error_handler("CrossCorroborator", TIER_BALANCED)
)

app = to_a2a(corroborator)

if __name__ == "__main__":
    port = int(os.getenv("CORROBORATOR_PORT", settings.CORROBORATOR_PORT))
    print(f"[*] Starting CrossCorroborator on port {port} with model {get_model(TIER_BALANCED)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
