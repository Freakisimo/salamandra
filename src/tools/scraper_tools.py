import requests
from bs4 import BeautifulSoup

def scrape_news_article(url: str) -> str:
    """
    Descarga y extrae el texto limpio y metadatos de un artículo periodístico a partir de su URL.
    
    Args:
        url: La dirección web del artículo de noticias.
        
    Returns:
        Texto limpio del artículo con título y párrafos clave.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        return f"URL inválida: {url}. Debe comenzar con http:// o https://"
        
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 SalamandraBot/1.0"
        )
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Remove noisy elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            element.decompose()
            
        title = soup.find("h1")
        title_text = title.get_text(strip=True) if title else "Título no identificado"
        
        # Look for article container or paragraphs
        article = soup.find("article") or soup.find("main") or soup.find("body")
        paragraphs = []
        if article:
            for p in article.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 30: # Filter short ads/disclaimers
                    paragraphs.append(txt)
                    
        body_text = "\n\n".join(paragraphs[:20]) # Limit to top 20 paragraphs to prevent excessive tokens
        
        if not body_text:
            body_text = soup.get_text(separator="\n", strip=True)[:4000]
            
        return f"Título: {title_text}\nURL: {url}\n\nContenido:\n{body_text}"
        
    except Exception as e:
        return f"Error al extraer el artículo desde {url}: {str(e)}"
