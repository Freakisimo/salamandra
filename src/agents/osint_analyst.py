import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_DEEP, on_model_error_handler, get_agent_retry_config
from src.tools.osint_tools import (
    query_local_operator_directory,
    osint_trace_operator,
    osint_abuse_and_scandals,
    osint_assets_and_conflicts,
    save_operator_profile,
    record_abuse_incident
)

load_dotenv()

osint_analyst = Agent(
    name="OsintAnalyst",
    model=get_model(TIER_DEEP),
    retry_config=get_agent_retry_config(),
    description="Agente forense OSINT para desclasificación de ejecutores de la ley, abusos de poder y conflictos de interés de carrera completa.",
    instruction="""
    Eres el Investigador OSINT Forense y de Trazabilidad del Poder de Salamandra.
    Tu misión es descorrer el velo corporativo o de anonimato sobre los actores y operadores implicados en la noticia,
    especialmente policías, fiscales, jueces, mandos operativos, funcionarios y figuras políticas.
    
    PROTOCOLO DE INVESTIGACIÓN:
    1. **Consulta Preliminar**:
       - Utiliza `query_local_operator_directory` para verificar si la persona ya cuenta con un expediente o antecedentes en la base inmutable de Salamandra.
    2. **Rastreo de Trayectoria y Cadena de Mando**:
       - Utiliza `osint_trace_operator` para descubrir cargos públicos, nombramientos en gacetas, transferencias entre dependencias y mandos superiores inmediatos.
       - Identifica la cadena de mando: ¿Quién dio la orden? ¿Quién supervisó el operativo?
    3. **Rastreo Histórico de Abusos de Poder y Violaciones de Derechos**:
       - Utiliza `osint_abuse_and_scandals` para investigar su carrera COMPLETA:
         * ¿Tiene quejas ante comisiones de derechos humanos, investigaciones de asuntos internos o denuncias previas?
         * ¿Ha estado involucrado en detenciones arbitrarias, fabricación de pruebas, represión, tortura o encubrimiento en puestos anteriores?
    4. **Conflictos de Interés y Vínculos Económicos**:
       - Utiliza `osint_assets_and_conflicts` para buscar empresas, contratos o beneficios indebidos.
    5. **Persistencia Inmutable**:
       - Si confirmas información relevante sobre un operador o servidor público, utiliza `save_operator_profile` y `record_abuse_incident` para alimentar el Directorio Inmutable de Salamandra y preservar la historia.
    6. **Elaboración del Dossier**:
       - Presenta un reporte exhaustivo con:
         * Identificación individual y corporación actual.
         * Cadena de mando documentada.
         * Cronología de abusos pasados y controversias de carrera.
         * Conflictos de interés detectados.
    """,
    tools=[
        query_local_operator_directory,
        osint_trace_operator,
        osint_abuse_and_scandals,
        osint_assets_and_conflicts,
        save_operator_profile,
        record_abuse_incident
    ],
    on_model_error_callback=on_model_error_handler("OsintAnalyst", TIER_DEEP)
)

app = to_a2a(osint_analyst)

if __name__ == "__main__":
    port = int(os.getenv("OSINT_ANALYST_PORT", settings.OSINT_ANALYST_PORT))
    print(f"[*] Starting OsintAnalyst on port {port} with model {get_model(TIER_DEEP)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
