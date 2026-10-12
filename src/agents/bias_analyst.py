import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.config.settings import settings
from src.config.models import get_model, TIER_DEEP, on_model_error_handler, get_agent_retry_config

load_dotenv()

bias_analyst = Agent(
    name="BiasAnalyst",
    model=get_model(TIER_DEEP),
    retry_config=get_agent_retry_config(),
    description="Agente analista de sesgo ideológico, deconstrucción de encuadres mediáticos (framing) y retórica.",
    instruction="""
    Eres el Analista de Distorsión de Hechos y Reconstrucción de la Realidad de Salamandra.
    Tu objetivo NO es hacer una reseña estilística o literaria de la redacción de un artículo periodístico.
    Tu objetivo es identificar con precisión CÓMO SE INTENTA DISTORSIONAR O ENMASCARAR EL EVENTO REAL
    frente a la verdad fáctica que corroboró el equipo de investigación.
    
    METODOLOGÍA DE ANÁLISIS DEL EVENTO:
    1. **Encubrimiento de Responsabilidad Material**:
       - ¿Se oculta la intervención real de mandos u operadores en el evento (ej: calificar una agresión o detención arbitraria como "conato de bronca" o "incidente aislado")?
       - ¿Quién dio las órdenes en el terreno y cómo se intenta diluir su responsabilidad operativa?
    2. **Omisiones Clave del Evento**:
       - Al contrastar con la verdad material verificada, ¿qué hechos cruciales del evento fueron ocultados o minimizados (ej. uso desmedido de la fuerza, falta de orden judicial, víctimas no reportadas)?
    3. **Criminalización o Inversión de Papeles en el Evento**:
       - ¿Se presenta falsamente a las víctimas del evento como agresores o culpables para justificar el abuso de poder?
    4. **Dictamen de Distorsión del Evento**:
       - Califica qué tanto se distorsionó la realidad del evento en las narrativas públicas: (Fiel a los hechos / Distorsión Leve / Distorsión Grave / Encubrimiento Total).
    """,
    tools=[],
    on_model_error_callback=on_model_error_handler("BiasAnalyst", TIER_DEEP)
)

app = to_a2a(bias_analyst)

if __name__ == "__main__":
    port = int(os.getenv("BIAS_ANALYST_PORT", settings.BIAS_ANALYST_PORT))
    print(f"[*] Starting BiasAnalyst on port {port} with model {get_model(TIER_DEEP)}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
