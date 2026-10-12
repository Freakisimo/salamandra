-- Schema for Salamandra Immutable Directory & Abuse of Power Traceability

CREATE TABLE IF NOT EXISTS operators (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    aliases TEXT,
    sector TEXT NOT NULL, -- Policial, Ministerial/Fiscalía, Judicial, Militar, Administrativo, Corporativo
    agency TEXT NOT NULL,
    rank_or_role TEXT,
    badge_or_id TEXT,
    superiors_chain TEXT, -- Cadena de mando: jefes inmediatos, mandos superiores documentados
    subordinates_scope TEXT, -- Área o fuerza bajo su mando operativo
    political_affiliations TEXT,
    tenure_period TEXT, -- Período o fechas en el cargo / antigüedad
    profile_details TEXT, -- Formación académica, cédula profesional o trayectoria pública
    contact_info TEXT, -- Teléfono o correo electrónico institucional público
    office_location TEXT, -- Despacho, oficina o sede oficial
    jurisdiction TEXT, -- Entidad federativa o ámbito jurisdiccional (ej. Jalisco, Ciudad de México, Federal)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_operators_normalized ON operators(normalized_name);
CREATE INDEX IF NOT EXISTS idx_operators_sector ON operators(sector);
CREATE INDEX IF NOT EXISTS idx_operators_agency ON operators(agency);
CREATE INDEX IF NOT EXISTS idx_operators_jurisdiction ON operators(jurisdiction);

CREATE TABLE IF NOT EXISTS abuse_incidents (
    id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL,
    incident_type TEXT NOT NULL, -- Detención arbitraria, Fabricación de pruebas, Tortura/Trato cruel, Desacato a amparo, Represión, Ocultamiento, Extralimitación, Corrupción
    incident_date TEXT,
    location TEXT,
    description TEXT NOT NULL,
    victims_summary TEXT,
    investigation_status TEXT, -- Impune, Queja DDHH, Investigación Asuntos Internos, Suspensión, Ratificado
    evidence_hashes TEXT, -- Hash SHA-256 de videos, actas, declaraciones o documentos
    sources_json TEXT, -- URLs y referencias bibliográficas/hemerográficas
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(operator_id) REFERENCES operators(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_abuse_operator ON abuse_incidents(operator_id);
CREATE INDEX IF NOT EXISTS idx_abuse_type ON abuse_incidents(incident_type);

CREATE TABLE IF NOT EXISTS conflicts_of_interest (
    id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    relation_type TEXT NOT NULL, -- Socio, Familiar, Contratista adjudicado, Proveedor de seguridad
    description TEXT NOT NULL,
    estimated_amount TEXT,
    sources_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(operator_id) REFERENCES operators(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS news_investigations (
    id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    corroborated_facts TEXT,
    detected_biases TEXT,
    final_report TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_operator_links (
    id TEXT PRIMARY KEY,
    news_id TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    role_in_event TEXT NOT NULL, -- Mando operativo, Ejecutor material, Vocero institucional, Encubridor, Testigo
    notes TEXT,
    FOREIGN KEY(news_id) REFERENCES news_investigations(id) ON DELETE CASCADE,
    FOREIGN KEY(operator_id) REFERENCES operators(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_link_news ON news_operator_links(news_id);
CREATE INDEX IF NOT EXISTS idx_link_operator ON news_operator_links(operator_id);
