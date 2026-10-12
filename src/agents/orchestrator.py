import os
import uuid
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
import httpx

from src.config.settings import settings
from src.config.models import get_model, TIER_DEEP, on_model_error_handler, get_agent_retry_config
from src.core.a2a_client import call_a2a_agent, extract_text_from_a2a_response
from src.core.registry import registry
from src.storage.person_directory import PersonDirectory
from src.storage.ledger import AuditLedger

load_dotenv()

def call_agent(agent_name: str, task: str) -> str:
    """
    Delega una subtarea específica a uno de los agentes de investigación registrados en Salamandra.
    
    Agentes disponibles:
    - FactExtractor: Extrae hechos atómicos, fechas, cifras y actores implicados.
    - GovDirectoryScout: Revisa directorios gubernamentales, organigramas y filtra mandos clave.
    - CrossCorroborator: Contrasta afirmaciones en fuentes de diversas orientaciones y agencias.
    - SourceAnalyst: Audita la propiedad, línea editorial y financiamiento del medio emisor.
    - OsintAnalyst: Investiga la trayectoria, abusos históricos de poder y cadena de mando de operadores.
    - BiasAnalyst: Deconstruye el encuadre (framing), adjetivación emotiva y sesgo del texto.
    
    Args:
        agent_name: Nombre del agente a invocar (FactExtractor, GovDirectoryScout, CrossCorroborator, SourceAnalyst, OsintAnalyst, BiasAnalyst).
        task: Descripción detallada de la tarea y datos requeridos para el agente.
        
    Returns:
        El resultado de la investigación devuelto por el agente.
    """
    return call_a2a_agent(agent_name=agent_name, task=task)

orchestrator = Agent(
    name="SalamandraOrchestrator",
    model=get_model(TIER_DEEP),
    retry_config=get_agent_retry_config(),
    description="Orquestador principal de Salamandra para dictaminar la veracidad objetiva de un evento, desclasificar operadores y emitir un veredicto fáctico sobre los hechos acontecidos.",
    instruction="""
    Eres el Orquestador de Verdad Objetiva y Transparencia de Salamandra.
    
    REGLA FUNDAMENTAL DE ENFOQUE:
    Tu objeto de estudio, investigación y dictamen final es EL EVENTO EN SÍ MISMO (los hechos materiales acontecidos en la realidad), NO una reseña u opinión sobre el artículo de internet o el medio de donde se tomó la noticia.
    El texto o enlace web aportado sirve ÚNICAMENTE como punto de partida o hipótesis inicial para descubrir qué evento ocurrió.
    NO dediques secciones a opinar sobre la redacción o el estilo periodístico de la nota web (evita juzgar el uso de adjetivos, voz pasiva o la prosa del medio).
    Toda tu conclusión y juicio de valor debe recaer sobre la veracidad del EVENTO, la actuación real de las autoridades/implicados y la legalidad o abusos del hecho.
    
    FLUJO DE INVESTIGACIÓN:
    1. **Fase 1: Identificación del Evento y Actores**:
       - Llama a `FactExtractor` para aislar las afirmaciones sobre el evento: qué ocurrió, fecha, lugar, corporaciones y personas involucradas.
    2. **Fase 2: Mapeo de Estructura Institucional y Filtro**:
       - Llama a `GovDirectoryScout` con la corporación, estado y zona del evento para identificar y registrar en el Directorio Inmutable a los mandos en campo y mandos superiores responsables de la jurisdicción.
    3. **Fase 3: OSINT Forense de los Operadores del Evento**:
       - Llama a `OsintAnalyst` con los 1-2 mandos clave para rastrear su historial de abusos pasados, antecedentes de carrera y cadena de mando vinculada al evento.
    4. **Fase 4: Contrastación Fáctica del Evento**:
       - Llama a `CrossCorroborator` para cotejar si el evento ocurrió tal como se alega, contrastando múltiples fuentes independientes, registros oficiales y evidencias.
       - Llama a `SourceAnalyst` para verificar si la fuente tiene conflictos de interés directos con los actores del evento.
    5. **Fase 5: Detección de Distorsión o Encubrimiento del Evento**:
       - Llama a `BiasAnalyst` para evidenciar cómo se intentó encubrir, maquillar o distorsionar la gravedad material del evento en las declaraciones públicas.
    6. **Fase 6: Síntesis y Dictamen sobre el Evento**:
       - Redacta el informe final estructurado en Markdown riguroso enfocado 100% en el EVENTO:
         * **# 1. Dictamen de Veracidad del Evento (Certeza Fáctica: 0-100%)**
           - Declaración contundente: ¿El evento alegado ocurrió en la realidad? (Verídico / Parcialmente distorsionado / Sin sustento / Fabricado).
         * **# 2. Reconstrucción Material de los Hechos**
           - Cronología exacta de qué pasó en el terreno: quién actuó, qué órdenes se dieron y qué consecuencias materiales ocurrieron.
         * **# 3. Contrastación de Hechos vs. Narrativas Oficiales o Interesadas**
           - Qué hechos materiales quedaron demostrados fehacientemente frente a las declaraciones oficiales o versiones de los involucrados.
         * **# 4. Operadores del Poder y Cadena de Mando Responsable**
           - Mandos identificados en la ejecución del evento, corporaciones, superiores documentados y antecedentes registrados en el Directorio Inmutable.
         * **# 5. Dictamen y Valoración Objetiva sobre el Evento**
           - Juicio y opinión fundamentada sobre el EVENTO en sí: legalidad, gravedad de la actuación, existencia de abusos de poder o violaciones a derechos, y responsabilidades materiales concluyentes.
    """,
    tools=[call_agent],
    on_model_error_callback=on_model_error_handler("SalamandraOrchestrator", TIER_DEEP)
)

# Base A2A Starlette App
app = to_a2a(orchestrator)

# Mount Web Interface & Static Files
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

async def home_ui(request):
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Salamandra UI no encontrada</h1>", status_code=404)

async def api_investigate(request):
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return JSONResponse({"error": "La consulta no puede estar vacía"}, status_code=400)
            
        task_prompt = (
            f"Investiga y dictamina la veracidad objetiva del EVENTO acontecido a partir de la siguiente referencia: {query}. "
            f"Coordina a la flota de agentes (FactExtractor, GovDirectoryScout, CrossCorroborator, SourceAnalyst, OsintAnalyst, BiasAnalyst). "
            f"REGLA OBLIGATORIA: El informe y tu dictamen final deben centrarse estrictamente en la veracidad y valoración sobre el EVENTO EN SÍ MISMO "
            f"(lo que ocurrió materialmente en los hechos y la responsabilidad de los operadores), NO en realizar una crítica literaria o reseña de estilo sobre el artículo de internet."
        )
        
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "id": "1",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": task_prompt}]
                }
            }
        }
        
        port = int(os.getenv("ORCHESTRATOR_PORT", settings.ORCHESTRATOR_PORT))
        # Extended 600s timeout to allow full multi-agent investigation sequence
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=600.0) as client:
            resp = await client.post("/", json=payload)
            data = resp.json()

        report_text = extract_text_from_a2a_response(data)
        
        # Auto-persist report and URL to database & immutable ledger
        inv_id = None
        if report_text and not report_text.startswith("Error"):
            try:
                directory = PersonDirectory()
                title = query[:90]
                for line in report_text.splitlines():
                    clean_l = line.strip().lstrip("#").strip()
                    if clean_l and len(clean_l) > 5 and not clean_l.lower().startswith("índice"):
                        title = clean_l[:120]
                        break
                saved = directory.save_investigation(
                    title=title,
                    query_or_url=query,
                    final_report=report_text
                )
                inv_id = saved.get("id")
            except Exception as save_err:
                print(f"[!] Warning: failed to auto-save investigation: {save_err}")

        return JSONResponse({
            "status": "success",
            "report": report_text,
            "investigation_id": inv_id
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_directory(request):
    try:
        q = request.query_params.get("q", "")
        sector = request.query_params.get("sector", "")
        jurisdiction = request.query_params.get("jurisdiction", "")
        agency = request.query_params.get("agency", "")
        status = request.query_params.get("status", "")
        directory = PersonDirectory()
        operators = directory.search_operators(
            query=q,
            sector=sector,
            jurisdiction=jurisdiction,
            agency=agency,
            status=status
        )
        return JSONResponse(operators)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_directory_filters(request):
    try:
        directory = PersonDirectory()
        opts = directory.get_directory_filter_options()
        return JSONResponse(opts)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_operator_dossier(request):
    try:
        operator_id = request.path_params.get("id", "")
        directory = PersonDirectory()
        dossier = directory.get_operator_dossier(operator_id)
        if not dossier:
            return JSONResponse({"error": "Operador no encontrado"}, status_code=404)
        return JSONResponse(dossier)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_investigations_list(request):
    try:
        start_date = request.query_params.get("start_date", "")
        end_date = request.query_params.get("end_date", "")
        q = request.query_params.get("q", "")
        directory = PersonDirectory()
        investigations = directory.list_investigations(
            start_date=start_date,
            end_date=end_date,
            query=q,
            limit=100
        )
        return JSONResponse(investigations)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_investigation_detail(request):
    try:
        inv_id = request.path_params.get("id", "")
        directory = PersonDirectory()
        inv = directory.get_investigation(inv_id)
        if not inv:
            return JSONResponse({"error": "Informe no encontrado"}, status_code=404)
        return JSONResponse(inv)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_ledger(request):
    try:
        ledger = AuditLedger()
        valid, msg = ledger.verify_integrity()
        entries = ledger.read_all_entries()
        return JSONResponse({"valid": valid, "message": msg, "entries": entries})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

app.add_route("/", home_ui, methods=["GET"])
app.add_route("/api/investigate", api_investigate, methods=["POST"])
app.add_route("/api/directory/filters", api_directory_filters, methods=["GET"])
app.add_route("/api/directory", api_directory, methods=["GET"])
app.add_route("/api/directory/{id}", api_operator_dossier, methods=["GET"])
app.add_route("/api/investigations", api_investigations_list, methods=["GET"])
app.add_route("/api/investigations/{id}", api_investigation_detail, methods=["GET"])
app.add_route("/api/ledger", api_ledger, methods=["GET"])

if __name__ == "__main__":
    port = int(os.getenv("ORCHESTRATOR_PORT", settings.ORCHESTRATOR_PORT))
    print(f"[*] Starting SalamandraOrchestrator on port {port} with model {get_model(TIER_DEEP)}...")
    print(f"[*] Web Interface available at: http://localhost:{port}/")
    uvicorn.run(app, host="0.0.0.0", port=port)
