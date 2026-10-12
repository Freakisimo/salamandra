from typing import List, Dict, Any
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

def search_web(query: str, max_results: int = 5) -> str:
    """
    Realiza una búsqueda web general con DuckDuckGo para obtener fuentes y contexto.
    
    Args:
        query: Consulta de búsqueda.
        max_results: Número de resultados máximos (por defecto 5).
        
    Returns:
        Cadena formateada con títulos, enlaces y resúmenes.
    """
    try:
        results = list(DDGS().text(query, max_results=max_results))
        if not results:
            return f"No se encontraron resultados para: {query}"
        formatted = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            formatted.append(f"Título: {title}\nEnlace: {href}\nFragmento: {body}\n")
        return "\n---\n".join(formatted)
    except Exception as e:
        return f"Error en búsqueda web: {str(e)}"

def search_news(query: str, max_results: int = 5) -> str:
    """
    Busca artículos periodísticos recientes en DuckDuckGo News.
    
    Args:
        query: Tema o titular de la noticia.
        max_results: Máximo de artículos a recuperar.
        
    Returns:
        Lista de notas con fecha, medio, titular y extracto.
    """
    try:
        results = list(DDGS().news(query, max_results=max_results))
        if not results:
            # Fallback to text search if news returns empty
            return search_web(f"{query} noticias", max_results=max_results)
        formatted = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("url", "") or r.get("href", "")
            date = r.get("date", "")
            source = r.get("source", "")
            formatted.append(f"Medio: {source} | Fecha: {date}\nTitular: {title}\nEnlace: {href}\nExtracto: {body}\n")
        return "\n---\n".join(formatted)
    except Exception as e:
        return f"Error en búsqueda de noticias: {str(e)}"

def search_balanced_perspectives(claim: str) -> str:
    """
    Ejecuta consultas cruzadas para cotejar una afirmación desde diversos ángulos
    (comunicados oficiales, coberturas críticas y agencias independientes de noticias).
    
    Args:
        claim: La afirmación o hecho a corroborar.
        
    Returns:
        Resumen estructurado de resultados contrastados.
    """
    queries = [
        f"{claim} comunicado oficial datos",
        f"{claim} investigacion contradicciones",
        f"{claim} Reuters OR AP OR AFP"
    ]
    
    sections = []
    for q in queries:
        res = search_web(q, max_results=3)
        sections.append(f"### Consulta: '{q}'\n{res}\n")
        
    return "\n".join(sections)
