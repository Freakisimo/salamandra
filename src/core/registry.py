from dataclasses import dataclass
from typing import Dict, List, Optional
from src.config.settings import settings
from src.config.models import TIER_LIGHT, TIER_BALANCED, TIER_DEEP

@dataclass
class AgentModule:
    name: str
    script_path: str
    port: int
    tier: str
    description: str

class AgentRegistry:
    """
    Extensible registry for all Salamandra investigation agents.
    Allows easy plug-and-play addition of new verification modules.
    """
    def __init__(self):
        self._agents: Dict[str, AgentModule] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        # 1. Fact & Entity Extractor (Light)
        self.register(AgentModule(
            name="FactExtractor",
            script_path="src/agents/fact_extractor.py",
            port=settings.FACT_EXTRACTOR_PORT,
            tier=TIER_LIGHT,
            description="Extrae hechos verificables, fechas, cifras y actores/operadores de la ley."
        ))

        # 2. Multi-Source Cross Corroborator (Balanced)
        self.register(AgentModule(
            name="CrossCorroborator",
            script_path="src/agents/corroborator.py",
            port=settings.CORROBORATOR_PORT,
            tier=TIER_BALANCED,
            description="Contrasta afirmaciones cruzadas entre medios opuestos, fuentes neutras y boletines."
        ))

        # 3. Media & Source Credibility Analyst (Balanced)
        self.register(AgentModule(
            name="SourceAnalyst",
            script_path="src/agents/source_analyst.py",
            port=settings.SOURCE_ANALYST_PORT,
            tier=TIER_BALANCED,
            description="Analiza la línea editorial, dueños, financiamiento e historial del medio que publica."
        ))

        # 4. OSINT Investigator (Deep)
        self.register(AgentModule(
            name="OsintAnalyst",
            script_path="src/agents/osint_analyst.py",
            port=settings.OSINT_ANALYST_PORT,
            tier=TIER_DEEP,
            description="Rastrea antecedentes de carrera, abusos de poder pasados, cadena de mando y conflictos de interés."
        ))

        # 5. Bias & Framing Deconstruction Analyst (Deep)
        self.register(AgentModule(
            name="BiasAnalyst",
            script_path="src/agents/bias_analyst.py",
            port=settings.BIAS_ANALYST_PORT,
            tier=TIER_DEEP,
            description="Deconstruye encuadres ideológicos, adjetivación emotiva y falacias mediáticas."
        ))

        # 6. Government Directory & Institutional Scout (Balanced)
        self.register(AgentModule(
            name="GovDirectoryScout",
            script_path="src/agents/gov_directory_scout.py",
            port=settings.GOV_DIRECTORY_SCOUT_PORT,
            tier=TIER_BALANCED,
            description="Revisa directorios gubernamentales y organigramas por estado e institución, filtrando mandos para OSINT."
        ))

    def register(self, module: AgentModule):
        self._agents[module.name] = module
        # Also register lowercased key for case-insensitive lookup
        self._agents[module.name.lower()] = module

    def get_agent(self, name: str) -> Optional[AgentModule]:
        return self._agents.get(name) or self._agents.get(name.lower())

    def list_agents(self) -> List[AgentModule]:
        # Return unique list preserving order
        seen = set()
        unique = []
        for mod in self._agents.values():
            if mod.name not in seen:
                seen.add(mod.name)
                unique.append(mod)
        return unique

registry = AgentRegistry()
