import json
from typing import Optional, List
from src.tools.search_tools import search_web
from src.storage.person_directory import PersonDirectory
from src.storage.ledger import AuditLedger

# Instantiate singleton directory for agent tools
_directory = PersonDirectory()

def query_local_operator_directory(identifier: str) -> str:
    """
    Consulta el Directorio Inmutable de Salamandra para verificar si el actor u operador
    ya tiene antecedentes registrados, cadena de mando documentada o incidentes de abuso de poder.
    
    Args:
        identifier: Nombre completo, alias o ID del operador/funcionario.
        
    Returns:
        Dossier completo en Markdown si existe, o mensaje informando que es un nuevo actor.
    """
    operator = _directory.get_operator(identifier)
    if not operator:
        # Try search
        matches = _directory.search_operators(identifier)
        if matches:
            summary = [f"- {m['full_name']} ({m['agency']} - {m['rank_or_role'] or 'Sin cargo'}) [ID: {m['id']}]" for m in matches]
            return "Coincidencias preliminares encontradas en el directorio:\n" + "\n".join(summary)
        return f"El actor '{identifier}' no tiene registro previo en el Directorio de Salamandra. Se requiere investigación OSINT inicial."
        
    return _directory.generate_dossier_markdown(operator["id"])

def osint_trace_operator(name: str, agency: str = "") -> str:
    """
    Realiza un rastreo OSINT sobre un servidor público, mando policial, juez o ejecutor
    para ubicar cargos públicos, nombramientos en gacetas oficiales, antigüedad y cadena de mando.
    
    Args:
        name: Nombre completo del operador o funcionario.
        agency: Dependencia o institución a la que pertenece o perteneció (opcional).
        
    Returns:
        Resultados estructurados de gacetas, nombramientos y antecedentes laborales.
    """
    queries = [
        f'"{name}" {agency} nombramiento OR gaceta OR cargo OR trayectoria',
        f'"{name}" {agency} superior OR director OR mando OR operativo'
    ]
    
    results = []
    for q in queries:
        res = search_web(q, max_results=4)
        results.append(f"### Dork de Trayectoria: '{q}'\n{res}\n")
        
    return "\n".join(results)

def osint_abuse_and_scandals(name: str, aliases: str = "") -> str:
    """
    Rastrea de manera exhaustiva el historial de abusos de autoridad, violaciones a derechos
    humanos, quejas, detenciones arbitrarias, tortura, impunidad o controversias de carrera.
    
    Args:
        name: Nombre del operador investigado.
        aliases: Alias o apodos conocidos (opcional).
        
    Returns:
        Hallazgos de denuncias, recomendaciones de derechos humanos y notas hemerográficas.
    """
    alias_part = f'OR "{aliases}"' if aliases else ""
    queries = [
        f'"{name}" {alias_part} "derechos humanos" OR "abuso de autoridad" OR "queja" OR "recomendacion"',
        f'"{name}" {alias_part} "detencion arbitraria" OR "tortura" OR "fabricacion" OR "corrupcion" OR "impunidad"',
        f'"{name}" {alias_part} denuncia OR investigacion OR suspension OR fiscalia'
    ]
    
    results = []
    for q in queries:
        res = search_web(q, max_results=3)
        results.append(f"### Rastreo de Abusos/Escándalos: '{q}'\n{res}\n")
        
    return "\n".join(results)

def osint_assets_and_conflicts(name: str) -> str:
    """
    Investiga posibles conflictos de interés, empresas asociadas, contratos adjudicados
    o vínculos societarios del actor o sus familiares directos.
    
    Args:
        name: Nombre de la persona investigada.
        
    Returns:
        Registros de contratos, empresas y declaraciones patrimoniales detectadas.
    """
    queries = [
        f'"{name}" "registro publico de comercio" OR empresa OR socio OR accionista',
        f'"{name}" contrato OR licitacion OR adjudicacion OR "declaracion patrimonial"'
    ]
    
    results = []
    for q in queries:
        res = search_web(q, max_results=3)
        results.append(f"### Rastreo de Intereses y Contratos: '{q}'\n{res}\n")
        
    return "\n".join(results)

def save_operator_profile(
    full_name: str,
    sector: str,
    agency: str,
    rank_or_role: str = "",
    badge_or_id: str = "",
    superiors_chain: str = "",
    subordinates_scope: str = "",
    political_affiliations: str = "",
    tenure_period: str = "",
    profile_details: str = "",
    contact_info: str = "",
    office_location: str = "",
    jurisdiction: str = ""
) -> str:
    """
    Guarda o actualiza el perfil del operador en el Directorio Inmutable de Salamandra con fines de transparencia.
    
    Args:
        full_name: Nombre completo del operador.
        sector: Policial, Ministerial/Fiscalía, Judicial, Militar, Administrativo o Corporativo.
        agency: Institución o corporación.
        rank_or_role: Cargo o rango desempeñado.
        badge_or_id: Placa o identificador oficial (si se conoce).
        superiors_chain: Mandos o superiores documentados.
        subordinates_scope: Fuerzas o área bajo su mando.
        political_affiliations: Vínculos o filiación partidista.
        tenure_period: Periodo de funciones o fechas en el cargo.
        profile_details: Perfil profesional, formación o cédula.
        contact_info: Datos de contacto oficial o institucional.
        office_location: Sede u oficina oficial de trabajo.
        jurisdiction: Entidad federativa o estado (ej. Jalisco, Ciudad de México, Federal).
        
    Returns:
        Confirmación con el ID asignado.
    """
    res = _directory.upsert_operator(
        full_name=full_name,
        sector=sector,
        agency=agency,
        rank_or_role=rank_or_role or None,
        badge_or_id=badge_or_id or None,
        superiors_chain=superiors_chain or None,
        subordinates_scope=subordinates_scope or None,
        political_affiliations=political_affiliations or None,
        tenure_period=tenure_period or None,
        profile_details=profile_details or None,
        contact_info=contact_info or None,
        office_location=office_location or None,
        jurisdiction=jurisdiction or None
    )
    return f"Operador '{full_name}' registrado exitosamente en el directorio inmutable con ID: {res['id']}."

def record_abuse_incident(
    operator_name: str,
    incident_type: str,
    description: str,
    incident_date: str = "",
    location: str = "",
    victims_summary: str = "",
    investigation_status: str = "En investigación / Impune",
    sources: str = ""
) -> str:
    """
    Registra formalmente un incidente de abuso de poder en el expediente inmutable del operador.
    
    Args:
        operator_name: Nombre del operador implicado.
        incident_type: Tipo de incidente (Detención arbitraria, Fabricación, Uso excesivo de fuerza, etc.).
        description: Narración fáctica de los hechos.
        incident_date: Fecha del suceso (opcional).
        location: Lugar de los hechos (opcional).
        victims_summary: Personas o colectivos afectados.
        investigation_status: Estatus judicial o administrativo.
        sources: Lista de enlaces o referencias separadas por coma.
        
    Returns:
        Confirmación de registro inmutable.
    """
    sources_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else []
    res = _directory.log_abuse_incident(
        operator_name_or_id=operator_name,
        incident_type=incident_type,
        description=description,
        incident_date=incident_date or None,
        location=location or None,
        victims_summary=victims_summary or None,
        investigation_status=investigation_status,
        sources=sources_list
    )
    return f"Incidente '{incident_type}' registrado exitosamente en el expediente de {operator_name} (ID: {res['incident_id']})."

def inspect_institution_cache(agency: str, sector: str = "") -> str:
    """
    Revisa en el Directorio Inmutable de Salamandra si ya existen mandos u operadores
    previamente mapeados para una corporación o institución gubernamental.
    
    Args:
        agency: Nombre de la corporación o institución (ej. Secretaría de Seguridad Ciudadana, Fiscalía).
        sector: Sector policial, ministerial, judicial, etc. (opcional).
        
    Returns:
        Lista de mandos ya registrados con sus cargos y cadenas de mando, o aviso de ausencia.
    """
    matches = _directory.search_operators(agency)
    if not matches and sector:
        matches = _directory.search_operators(sector)
        
    if not matches:
        return f"No hay mandos registrados en caché local para la institución '{agency}'. Se requiere rastreo en gacetas y directorios oficiales."
        
    summary = []
    for m in matches:
        summary.append(
            f"- **{m['full_name']}** ({m['agency']} - {m['rank_or_role'] or 'Sin cargo especificado'})\n"
            f"  * Cadena de Mando: {m['superiors_chain'] or 'No documentada'}\n"
            f"  * Área de Mando / Subordinados: {m['subordinates_scope'] or 'General'}\n"
            f"  * ID: `{m['id']}`"
        )
    return "Mandos encontrados previamente en el Directorio Local de Salamandra:\n" + "\n".join(summary)

def search_gov_organigram(institution: str, jurisdiction: str, sector_or_zone: str = "") -> str:
    """
    Rastrea directorios de servidores públicos, organigramas estructurales,
    nóminas de transparencia y gacetas de nombramientos oficiales para mapear la cadena de mando.
    
    Args:
        institution: Dependencia gubernamental o corporación (ej. Secretaría de Seguridad, Fiscalía).
        jurisdiction: Estado, municipio o demarcación geográfica (ej. CDMX, Jalisco, Monterrey).
        sector_or_zone: Área, zona o sector específico (ej. Zona Centro, Cuauhtémoc, Región V).
        
    Returns:
        Resultados de búsqueda orientados a nombres de directores, comandantes y secretarios.
    """
    zone_query = f'"{sector_or_zone}"' if sector_or_zone else ""
    queries = [
        f'"{institution}" "{jurisdiction}" {zone_query} "directorio de servidores publicos" OR organigrama OR titular',
        f'"{institution}" "{jurisdiction}" {zone_query} "director operativo" OR "subsecretario" OR "comandante de sector"',
        f'"{institution}" "{jurisdiction}" nombramiento OR gaceta OR "toma de protesta"'
    ]
    
    results = []
    for q in queries:
        res = search_web(q, max_results=3)
        results.append(f"### Dork Institucional: '{q}'\n{res}\n")
        
    return "\n".join(results)

