import pytest
from google.adk.agents import Agent
from starlette.applications import Starlette

def test_agents_instantiation_and_a2a_apps():
    from src.agents.fact_extractor import fact_extractor, app as app_fact
    from src.agents.gov_directory_scout import gov_directory_scout, app as app_gov
    from src.agents.corroborator import corroborator, app as app_corr
    from src.agents.source_analyst import source_analyst, app as app_source
    from src.agents.osint_analyst import osint_analyst, app as app_osint
    from src.agents.bias_analyst import bias_analyst, app as app_bias
    from src.agents.orchestrator import orchestrator, app as app_orch

    agents = [
        (fact_extractor, app_fact, "FactExtractor"),
        (gov_directory_scout, app_gov, "GovDirectoryScout"),
        (corroborator, app_corr, "CrossCorroborator"),
        (source_analyst, app_source, "SourceAnalyst"),
        (osint_analyst, app_osint, "OsintAnalyst"),
        (bias_analyst, app_bias, "BiasAnalyst"),
        (orchestrator, app_orch, "SalamandraOrchestrator"),
    ]

    for ag, app, expected_name in agents:
        assert isinstance(ag, Agent)
        assert ag.name == expected_name
        assert isinstance(app, Starlette) or callable(app)
