import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_LIGHT, on_model_error_handler, get_agent_retry_config
from src.tools.scraper_tools import scrape_news_article

load_dotenv()

fact_extractor = Agent(
    name="FactExtractor",
    model=get_model(TIER_LIGHT),
    description="Agente especializado en extracción de hechos atómicos y desclasificación de actores.",
    instruction="""
    Eres el Agente Extractor de Hechos y Entidades de Salamandra.
    Tu misión es procesar una noticia (texto o URL) y aislar estrictamente los hechos puros y los actores participantes:
    
    1. Si el usuario te envía un enlace (URL), utiliza la herramienta `scrape_news_article` para obtener el contenido completo.
    2. Identifica y desglosa:
       - **Medio Emisor Original**: Nombre del diario, portal o autor.
       - **Afirmaciones Fácticas Atómicas**: Hechos objetivos (quién, qué, cuándo, dónde, cifras exactas y citas textuales).
       - **Actores y Operadores Implicados**: Individualiza a todas las personas mencionadas, especialmente:
         * Servidores públicos, policías, fiscales, jueces, mandos operativos, militares o inspectores.
         * Institución o corporación a la que pertenecen.
         * Su rol explícito en el evento (quién ordenó, quién ejecutó, quién declaró).
       - **Juicios de Valor y Adjetivos del Texto**: Identifica qué partes de la nota son opiniones, adjetivos calificativos o interpretaciones del reportero y sepáralas de los hechos.
       
    Sé riguroso, estructurado y neutral.
    """,
    tools=[scrape_news_article],
    retry_config=get_agent_retry_config(),
    on_model_error_callback=on_model_error_handler("FactExtractor", TIER_LIGHT)
)

app = to_a2a(fact_extractor)

if __name__ == "__main__":
    port = int(os.getenv("FACT_EXTRACTOR_PORT", settings.FACT_EXTRACTOR_PORT))
    print(f"[*] Starting FactExtractor on port {port} with model {get_model(TIER_LIGHT)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
