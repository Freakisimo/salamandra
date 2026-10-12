import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_BALANCED, on_model_error_handler, get_agent_retry_config
from src.tools.search_tools import search_web, search_news

load_dotenv()

source_analyst = Agent(
    name="SourceAnalyst",
    model=get_model(TIER_BALANCED),
    retry_config=get_agent_retry_config(),
    description="Agente investigador de la línea editorial, dueños, financiamiento e intereses del medio de comunicación.",
    instruction="""
    Eres el Auditor de Fuentes y Medios de Comunicación de Salamandra.
    Tu misión es investigar la credibilidad, intereses económicos y afinidad ideológica del medio emisor de la noticia.
    
    METODOLOGÍA:
    1. Utiliza `search_web` para investigar al medio o periodista que publica la nota:
       - **Propiedad y Conglomerado**: ¿Quién es el dueño o grupo empresarial detrás del medio? ¿Qué otros intereses económicos tienen en telecomunicaciones, construcción, energía o banca?
       - **Línea Editorial e Historial**: ¿Tiene inclinación ideológica declarada o recurrente (conservadora, progresista, oficialista, de oposición)?
       - **Dependencia de Publicidad / Financiamiento**: ¿Recibe montos significativos de publicidad oficial del gobierno en turno, fondos extranjeros o donaciones de grupos de interés?
       - **Historial de Desinformación**: ¿Tiene antecedentes de noticias falsas, rectificaciones forzadas o sanciones deontológicas?
    2. Evalúa si el medio tiene un conflicto de interés directo respecto al tema o personas de la noticia actual.
    """,
    tools=[search_web, search_news],
    on_model_error_callback=on_model_error_handler("SourceAnalyst", TIER_BALANCED)
)

app = to_a2a(source_analyst)

if __name__ == "__main__":
    port = int(os.getenv("SOURCE_ANALYST_PORT", settings.SOURCE_ANALYST_PORT))
    print(f"[*] Starting SourceAnalyst on port {port} with model {get_model(TIER_BALANCED)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
