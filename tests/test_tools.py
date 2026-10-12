import pytest
from src.tools.scraper_tools import scrape_news_article
from src.tools.osint_tools import (
    save_operator_profile,
    record_abuse_incident,
    query_local_operator_directory
)

def test_scraper_invalid_url():
    res = scrape_news_article("not_a_url")
    assert "URL inválida" in res

def test_osint_local_directory_flow():
    # Save a test operator profile
    res_save = save_operator_profile(
        full_name="Juez Penal Samuel Gomez",
        sector="Judicial",
        agency="Tribunal Superior de Justicia",
        rank_or_role="Juez de Control",
        superiors_chain="Presidente del Tribunal",
        political_affiliations="Sin partido"
    )
    assert "registrado exitosamente" in res_save
    
    # Record abuse
    res_inc = record_abuse_incident(
        operator_name="Juez Penal Samuel Gomez",
        incident_type="Desacato a suspensión de amparo",
        description="Mantuvo en prisión preventiva oficiosa a ciudadano a pesar de contar con amparo definitivo"
    )
    assert "registrado exitosamente" in res_inc
    
    # Query dossier
    dossier = query_local_operator_directory("Juez Penal Samuel Gomez")
    assert "Dossier de Trazabilidad: Juez Penal Samuel Gomez" in dossier
    assert "Desacato a suspensión de amparo" in dossier
