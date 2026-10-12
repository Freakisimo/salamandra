import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_BALANCED, on_model_error_handler, get_agent_retry_config
from src.tools.osint_tools import (
    inspect_institution_cache,
    search_gov_organigram,
    save_operator_profile
)

load_dotenv()

gov_directory_scout = Agent(
    name="GovDirectoryScout",
    model=get_model(TIER_BALANCED),
    retry_config=get_agent_retry_config(),
    description="Agente puente para revisión de directorios gubernamentales, organigramas por estado e institución y filtrado selectivo para OSINT.",
    instruction="""
    Eres el Revisor de Directorios Gubernamentales y Organigramas de Salamandra.
    Tu misión es servir de puente entre el evento noticioso y la individualización de los operadores del poder.
    
    METODOLOGÍA DE INVESTIGACIÓN:
    1. **Recepción del Evento**:
       - Analiza la institución gubernamental, estado, municipio/alcaldía, zona o sector y tipo de operativo involucrado (ej. desalojo policial, cateo, detención, resolución judicial).
    2. **Consulta a Caché Local**:
       - Utiliza `inspect_institution_cache` para verificar si los mandos de esa corporación ya fueron mapeados y guardados en el Directorio Inmutable de Salamandra.
    3. **Rastreo de Organigramas y Gacetas**:
       - Si no se encuentran en local, utiliza `search_gov_organigram` para rastrear directorios oficiales, organigramas estructurales y gacetas de nombramiento en esa jurisdicción.
       - Identifica la cadena de mando funcional:
         * Titular institucional (Secretario, Fiscal General, Magistrado Presidente).
         * Mando operativo general (Subsecretario de Operación Policial, Comisionado).
         * Mando en campo/sector (Director Operativo de Zona, Comandante de Sector, Fiscal de Región).
    4. **Persistencia Preventiva**:
       - Registra a cada funcionario mapeado usando `save_operator_profile` indicando su cargo, corporación, área y superiores documentados. Esto asegura que no tengamos que volver a buscarlos en futuras noticias.
    5. **Filtrado Inteligente para OsintAnalyst**:
       - NO satures al agente OSINT con decenas de funcionarios administrativos.
       - Filtra y selecciona únicamente los **1 a 2 actores con mayor responsabilidad directa** en la orden o ejecución material del evento en cuestión.
       - Genera un briefing limpio con:
         * **Cadena de Mando Mapeada**: Estructura general de la corporación.
         * **Nuevos Actores Guardados en el Directorio**: Nombres y cargos archivados.
         * **Objetivos Filtrados para OSINT**: Lista priorizada (Nombre, Cargo y Justificación de por qué investigar sus antecedentes y posibles abusos pasados).
    """,
    tools=[
        inspect_institution_cache,
        search_gov_organigram,
        save_operator_profile
    ],
    on_model_error_callback=on_model_error_handler("GovDirectoryScout", TIER_BALANCED)
)

app = to_a2a(gov_directory_scout)

if __name__ == "__main__":
    port = int(os.getenv("GOV_DIRECTORY_SCOUT_PORT", settings.GOV_DIRECTORY_SCOUT_PORT))
    print(f"[*] Starting GovDirectoryScout on port {port} with model {get_model(TIER_BALANCED)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
