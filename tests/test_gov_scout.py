import uuid
import pytest
from src.tools.osint_tools import (
    inspect_institution_cache,
    search_gov_organigram,
    save_operator_profile
)
from src.agents.gov_directory_scout import gov_directory_scout

def test_institution_cache_and_persistence():
    unique_agency = f"Secretaría de Movilidad y Transporte {uuid.uuid4().hex[:8]}"
    
    # 1. Initially uncached
    uncached_res = inspect_institution_cache(unique_agency)
    assert "No hay mandos registrados en caché local" in uncached_res
    
    # 2. Persist new official
    save_res = save_operator_profile(
        full_name="Director Operativo Carlos Mendoza",
        sector="Administrativo/Transporte",
        agency=unique_agency,
        rank_or_role="Director de Inspección",
        superiors_chain="Secretario de Movilidad Titular",
        subordinates_scope="Zona Metropolitana de Monterrey"
    )
    assert "registrado exitosamente" in save_res
    
    # 3. Now cached
    cached_res = inspect_institution_cache(unique_agency)
    assert "Carlos Mendoza" in cached_res
    assert "Director de Inspección" in cached_res
    assert "Cadena de Mando" in cached_res

def test_search_gov_organigram_interface():
    res = search_gov_organigram(
        institution="Fiscalía General de Justicia",
        jurisdiction="Jalisco",
        sector_or_zone="Guadalajara"
    )
    assert "Dork Institucional" in res

def test_gov_scout_agent_properties():
    assert gov_directory_scout.name == "GovDirectoryScout"
    assert len(gov_directory_scout.tools) == 3
    tool_names = [t.__name__ for t in gov_directory_scout.tools]
    assert "inspect_institution_cache" in tool_names
    assert "search_gov_organigram" in tool_names
    assert "save_operator_profile" in tool_names
