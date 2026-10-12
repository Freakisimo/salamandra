import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config.settings import settings
from src.storage.ledger import AuditLedger

class PersonDirectory:
    """
    High-availability, portable directory for tracking operators,
    law enforcement actors, authority abuse incidents, and conflicts of interest.
    """
    def __init__(self, db_path: Optional[Path] = None, ledger: Optional[AuditLedger] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger or AuditLedger()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with self._get_connection() as conn:
                cur = conn.cursor()
                # Execute individual schema statements to allow graceful handling
                # if existing tables need column migrations before index creation
                for raw_stmt in schema_sql.split(";"):
                    stmt = raw_stmt.strip()
                    if stmt:
                        try:
                            cur.execute(stmt + ";")
                        except sqlite3.OperationalError:
                            # Might fail if index references column not yet migrated
                            pass
                conn.commit()

        # Automatic migrations for new transparency columns on existing databases
        with self._get_connection() as conn:
            cur = conn.cursor()
            for col in ["tenure_period", "profile_details", "contact_info", "office_location", "jurisdiction"]:
                try:
                    cur.execute(f"ALTER TABLE operators ADD COLUMN {col} TEXT;")
                except sqlite3.OperationalError:
                    pass

            # Ensure index on jurisdiction is created now that column is guaranteed to exist
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_operators_jurisdiction ON operators(jurisdiction);")
            except sqlite3.OperationalError:
                pass

            # Backfill jurisdiction for existing rows if null or empty
            cur.execute("""
                UPDATE operators 
                SET jurisdiction = CASE
                    WHEN LOWER(agency) LIKE '%jalisco%' OR LOWER(COALESCE(office_location, '')) LIKE '%jalisco%' THEN 'Jalisco'
                    WHEN LOWER(agency) LIKE '%cdmx%' OR LOWER(agency) LIKE '%ciudad de méxico%' OR LOWER(agency) LIKE '%seguridad ciudadana%' THEN 'Ciudad de México'
                    WHEN LOWER(agency) LIKE '%nuevo león%' OR LOWER(agency) LIKE '%monterrey%' THEN 'Nuevo León'
                    WHEN LOWER(agency) LIKE '%puebla%' THEN 'Puebla'
                    WHEN LOWER(agency) LIKE '%méxico%' OR LOWER(agency) LIKE '%edomex%' THEN 'Estado de México'
                    WHEN LOWER(agency) LIKE '%nacional%' OR LOWER(agency) LIKE '%federal%' OR LOWER(agency) LIKE '%fgr%' THEN 'Federal'
                    ELSE 'Jalisco'
                END
                WHERE jurisdiction IS NULL OR TRIM(jurisdiction) = '';
            """)
            conn.commit()

    @staticmethod
    def _extract_domain(url_or_query: str) -> str:
        if not url_or_query:
            return "Consulta directa"
        clean = url_or_query.strip()
        if clean.startswith("http://") or clean.startswith("https://"):
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(clean)
                netloc = parsed.netloc.lower()
                if netloc.startswith("www."):
                    netloc = netloc[4:]
                return netloc or "Web externa"
            except Exception:
                return "Web externa"
        return "Texto / Caso fáctico"

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.strip().lower().split())

    def upsert_operator(
        self,
        full_name: str,
        sector: str,
        agency: str,
        rank_or_role: Optional[str] = None,
        badge_or_id: Optional[str] = None,
        superiors_chain: Optional[str] = None,
        subordinates_scope: Optional[str] = None,
        aliases: Optional[str] = None,
        political_affiliations: Optional[str] = None,
        tenure_period: Optional[str] = None,
        profile_details: Optional[str] = None,
        contact_info: Optional[str] = None,
        office_location: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers or updates an individual operator / official with full transparency details."""
        norm_name = self.normalize_name(full_name)
        now = datetime.now(timezone.utc).isoformat()

        if not jurisdiction:
            agency_low = (agency or "").lower()
            office_low = (office_location or "").lower()
            comb = agency_low + " " + office_low
            if "jalisco" in comb or "guadalajara" in comb or "zapopan" in comb:
                jurisdiction = "Jalisco"
            elif "cdmx" in comb or "ciudad de méxico" in comb or "distrito federal" in comb or "seguridad ciudadana" in comb:
                jurisdiction = "Ciudad de México"
            elif "nuevo león" in comb or "monterrey" in comb:
                jurisdiction = "Nuevo León"
            elif "puebla" in comb:
                jurisdiction = "Puebla"
            elif "estado de méxico" in comb or "edomex" in comb:
                jurisdiction = "Estado de México"
            elif "federal" in comb or "nacional" in comb or "fgr" in comb:
                jurisdiction = "Federal"
            else:
                jurisdiction = "Federal"
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM operators WHERE normalized_name = ?", (norm_name,))
            existing = cur.fetchone()
            
            if existing:
                op_id = existing["id"]
                cur.execute("""
                    UPDATE operators SET
                        sector = COALESCE(?, sector),
                        agency = COALESCE(?, agency),
                        rank_or_role = COALESCE(?, rank_or_role),
                        badge_or_id = COALESCE(?, badge_or_id),
                        superiors_chain = COALESCE(?, superiors_chain),
                        subordinates_scope = COALESCE(?, subordinates_scope),
                        aliases = COALESCE(?, aliases),
                        political_affiliations = COALESCE(?, political_affiliations),
                        tenure_period = COALESCE(?, tenure_period),
                        profile_details = COALESCE(?, profile_details),
                        contact_info = COALESCE(?, contact_info),
                        office_location = COALESCE(?, office_location),
                        jurisdiction = COALESCE(?, jurisdiction),
                        updated_at = ?
                    WHERE id = ?
                """, (
                    sector, agency, rank_or_role, badge_or_id,
                    superiors_chain, subordinates_scope, aliases,
                    political_affiliations, tenure_period, profile_details,
                    contact_info, office_location, jurisdiction, now, op_id
                ))
                action = "UPDATE_OPERATOR"
            else:
                op_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO operators (
                        id, full_name, normalized_name, aliases, sector, agency,
                        rank_or_role, badge_or_id, superiors_chain, subordinates_scope,
                        political_affiliations, tenure_period, profile_details,
                        contact_info, office_location, jurisdiction, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    op_id, full_name, norm_name, aliases, sector, agency,
                    rank_or_role, badge_or_id, superiors_chain, subordinates_scope,
                    political_affiliations, tenure_period, profile_details,
                    contact_info, office_location, jurisdiction, now, now
                ))
                action = "REGISTER_OPERATOR"
                
            conn.commit()

        payload = {
            "id": op_id,
            "full_name": full_name,
            "normalized_name": norm_name,
            "sector": sector,
            "agency": agency,
            "rank_or_role": rank_or_role,
            "badge_or_id": badge_or_id,
            "superiors_chain": superiors_chain,
            "subordinates_scope": subordinates_scope,
            "tenure_period": tenure_period,
            "profile_details": profile_details,
            "contact_info": contact_info,
            "office_location": office_location,
            "jurisdiction": jurisdiction,
            "timestamp": now
        }
        self.ledger.append_entry(action=action, payload=payload)
        return payload

    def log_abuse_incident(
        self,
        operator_name_or_id: str,
        incident_type: str,
        description: str,
        incident_date: Optional[str] = None,
        location: Optional[str] = None,
        victims_summary: Optional[str] = None,
        investigation_status: str = "Sin sanción / En investigación",
        evidence_hashes: Optional[str] = None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Logs an abuse of authority or human rights violation committed by the operator."""
        operator = self.get_operator(operator_name_or_id)
        if not operator:
            # If operator doesn't exist, create minimal stub
            operator = self.upsert_operator(
                full_name=operator_name_or_id,
                sector="Por determinar",
                agency="Por determinar"
            )

        inc_id = str(uuid.uuid4())
        sources_str = json.dumps(sources or [], ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO abuse_incidents (
                    id, operator_id, incident_type, incident_date, location,
                    description, victims_summary, investigation_status,
                    evidence_hashes, sources_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inc_id, operator["id"], incident_type, incident_date, location,
                description, victims_summary, investigation_status,
                evidence_hashes, sources_str, now
            ))
            conn.commit()

        payload = {
            "incident_id": inc_id,
            "operator_id": operator["id"],
            "operator_name": operator["full_name"],
            "incident_type": incident_type,
            "incident_date": incident_date,
            "location": location,
            "description": description,
            "status": investigation_status,
            "sources": sources or [],
            "timestamp": now
        }
        self.ledger.append_entry(action="LOG_ABUSE_INCIDENT", payload=payload)
        return payload

    def get_operator(self, identifier: str) -> Optional[Dict[str, Any]]:
        norm = self.normalize_name(identifier)
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM operators 
                WHERE id = ? OR normalized_name = ?
            """, (identifier, norm))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def search_operators(
        self,
        query: str = "",
        sector: str = "",
        jurisdiction: str = "",
        agency: str = "",
        status: str = "",
        limit: int = 150
    ) -> List[Dict[str, Any]]:
        conditions = []
        having_conditions = []
        params: List[Any] = []
        
        if query and query.strip():
            clean_q = query.strip()
            norm = f"%{self.normalize_name(clean_q)}%"
            conditions.append("(o.normalized_name LIKE ? OR o.agency LIKE ? OR o.rank_or_role LIKE ? OR o.aliases LIKE ? OR o.id LIKE ? OR LOWER(COALESCE(o.office_location, '')) LIKE ?)")
            params.extend([norm, norm, norm, norm, f"%{clean_q.lower()}%", f"%{clean_q.lower()}%"])
            
        if sector and sector.strip() and sector.strip().lower() not in ("todos", "todas"):
            conditions.append("LOWER(o.sector) LIKE ?")
            params.append(f"%{sector.strip().lower()}%")

        if jurisdiction and jurisdiction.strip() and jurisdiction.strip().lower() not in ("todos", "todas"):
            clean_jur = jurisdiction.strip().lower()
            conditions.append("(LOWER(COALESCE(o.jurisdiction, '')) = ? OR LOWER(COALESCE(o.jurisdiction, '')) LIKE ? OR LOWER(o.agency) LIKE ? OR LOWER(COALESCE(o.office_location, '')) LIKE ?)")
            params.extend([clean_jur, f"%{clean_jur}%", f"%{clean_jur}%", f"%{clean_jur}%"])

        if agency and agency.strip() and agency.strip().lower() not in ("todos", "todas"):
            clean_agency = agency.strip().lower()
            conditions.append("(LOWER(o.agency) = ? OR LOWER(o.agency) LIKE ?)")
            params.extend([clean_agency, f"%{clean_agency}%"])

        # Status filter
        if status and status.strip():
            st_clean = status.strip().lower()
            if st_clean in ("con_reportes", "con_abusos", "abusos"):
                having_conditions.append("COUNT(ai.id) > 0")
            elif st_clean in ("sin_reportes", "sin_abusos", "limpio"):
                having_conditions.append("COUNT(ai.id) = 0")
            elif st_clean in ("en_investigacion", "investigacion", "impune"):
                having_conditions.append("SUM(CASE WHEN LOWER(ai.investigation_status) LIKE '%investiga%' OR LOWER(ai.investigation_status) LIKE '%impune%' THEN 1 ELSE 0 END) > 0")
            
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        having_clause = ("HAVING " + " AND ".join(having_conditions)) if having_conditions else ""
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT o.*, COUNT(ai.id) as incidents_count
                FROM operators o
                LEFT JOIN abuse_incidents ai ON o.id = ai.operator_id
                {where_clause}
                GROUP BY o.id
                {having_clause}
                ORDER BY incidents_count DESC, o.updated_at DESC
                LIMIT ?
            """, params + [limit])
            return [dict(r) for r in cur.fetchall()]

    def get_directory_filter_options(self) -> Dict[str, Any]:
        """Returns distinct filter choices for the UI directory filters."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT jurisdiction FROM operators 
                WHERE jurisdiction IS NOT NULL AND TRIM(jurisdiction) != ''
                ORDER BY jurisdiction ASC
            """)
            jurisdictions = [r[0] for r in cur.fetchall()]
            if not jurisdictions:
                jurisdictions = ["Jalisco", "Ciudad de México", "Federal"]

            cur.execute("""
                SELECT DISTINCT agency FROM operators 
                WHERE agency IS NOT NULL AND TRIM(agency) != ''
                ORDER BY agency ASC
            """)
            agencies = [r[0] for r in cur.fetchall()]

            cur.execute("""
                SELECT DISTINCT sector FROM operators 
                WHERE sector IS NOT NULL AND TRIM(sector) != ''
                ORDER BY sector ASC
            """)
            sectors = [r[0] for r in cur.fetchall()]

            return {
                "jurisdictions": jurisdictions,
                "agencies": agencies,
                "sectors": sectors,
                "statuses": [
                    {"id": "todos", "label": "Todos los estatus"},
                    {"id": "con_reportes", "label": "⚠️ Con reportes de abuso"},
                    {"id": "sin_reportes", "label": "✓ Sin antecedentes validados"},
                    {"id": "en_investigacion", "label": "⚖️ En investigación / Impune"}
                ]
            }

    def get_operator_incidents(self, operator_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM abuse_incidents
                WHERE operator_id = ?
                ORDER BY created_at DESC
            """, (operator_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_operator_dossier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves structured operator dossier data including full markdown and incident objects."""
        op = self.get_operator(identifier)
        if not op:
            return None
        incidents = self.get_operator_incidents(op["id"])
        # Format incidents sources
        parsed_incidents = []
        for inc in incidents:
            inc_dict = dict(inc)
            inc_dict["sources"] = json.loads(inc_dict.get("sources_json") or "[]")
            parsed_incidents.append(inc_dict)
            
        markdown = self.generate_dossier_markdown(op["id"])
        return {
            "operator": op,
            "incidents": parsed_incidents,
            "incidents_count": len(incidents),
            "dossier_markdown": markdown
        }

    def save_investigation(
        self,
        title: str,
        query_or_url: str,
        final_report: str,
        summary: Optional[str] = None,
        corroborated_facts: Optional[str] = None,
        detected_biases: Optional[str] = None,
        operator_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Saves a completed news/claim investigation report into the store and ledger, linking involved operators."""
        inv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Auto-extract summary from report if not provided
        if not summary and final_report:
            lines = [l.strip() for l in final_report.splitlines() if l.strip() and not l.strip().startswith("#")]
            summary = lines[0][:280] if lines else title
            
        linked_operators = []
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO news_investigations (
                    id, url, title, summary, corroborated_facts, detected_biases, final_report, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_id, query_or_url, title, summary or "",
                corroborated_facts or "", detected_biases or "",
                final_report, now
            ))

            # Fetch operators to match or link
            cur.execute("SELECT id, full_name, normalized_name, aliases, sector, agency, rank_or_role FROM operators")
            all_ops = [dict(r) for r in cur.fetchall()]
            
            search_corpus = f"{title} {query_or_url} {final_report}".lower()
            target_ids = set(operator_ids or [])

            for op in all_ops:
                op_id = op["id"]
                name_clean = op["full_name"].strip().lower()
                norm_name = op["normalized_name"].strip().lower()
                if len(name_clean) >= 4 and (name_clean in search_corpus or norm_name in search_corpus):
                    target_ids.add(op_id)
                elif op.get("aliases"):
                    for alias in op["aliases"].split(","):
                        alias_clean = alias.strip().lower()
                        if len(alias_clean) >= 4 and alias_clean in search_corpus:
                            target_ids.add(op_id)
                            break

            for op in all_ops:
                if op["id"] in target_ids:
                    cur.execute("SELECT 1 FROM news_operator_links WHERE news_id = ? AND operator_id = ?", (inv_id, op["id"]))
                    if not cur.fetchone():
                        link_id = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO news_operator_links (id, news_id, operator_id, role_in_event, notes)
                            VALUES (?, ?, ?, ?, ?)
                        """, (link_id, inv_id, op["id"], "Mando / Implicado", "Funcionario implicado identificado en la investigación"))
                    linked_operators.append({
                        "id": op["id"],
                        "full_name": op["full_name"],
                        "sector": op["sector"],
                        "agency": op["agency"],
                        "rank_or_role": op["rank_or_role"]
                    })

            conn.commit()
            
        payload = {
            "id": inv_id,
            "url": query_or_url,
            "title": title,
            "summary": summary,
            "operators_count": len(linked_operators),
            "timestamp": now
        }
        self.ledger.append_entry(action="LOG_INVESTIGATION", payload=payload)
        return {
            "id": inv_id,
            "url": query_or_url,
            "web_domain": self._extract_domain(query_or_url),
            "title": title,
            "summary": summary,
            "final_report": final_report,
            "operators": linked_operators,
            "created_at": now
        }

    def list_investigations(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieves past investigation reports ordered by latest first, with date/text filters and linked operators."""
        conditions = []
        params = []
        if start_date and start_date.strip():
            conditions.append("date(created_at) >= date(?)")
            params.append(start_date.strip())
        if end_date and end_date.strip():
            conditions.append("date(created_at) <= date(?)")
            params.append(end_date.strip())
        if query and query.strip():
            q_clean = f"%{query.strip().lower()}%"
            conditions.append("(LOWER(title) LIKE ? OR LOWER(url) LIKE ? OR LOWER(summary) LIKE ?)")
            params.extend([q_clean, q_clean, q_clean])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT id, url, title, summary, final_report, created_at
                FROM news_investigations
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, params + [limit])
            invs = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT id, full_name, normalized_name, aliases, sector, agency, rank_or_role FROM operators")
            all_ops = [dict(r) for r in cur.fetchall()]

            for inv in invs:
                cur.execute("""
                    SELECT o.id, o.full_name, o.sector, o.agency, o.rank_or_role, l.role_in_event, l.notes as relation_notes
                    FROM news_operator_links l
                    JOIN operators o ON l.operator_id = o.id
                    WHERE l.news_id = ?
                    ORDER BY o.full_name ASC
                """, (inv["id"],))
                ops = [dict(r) for r in cur.fetchall()]

                # Retroactive linking for records that predate the linking feature
                if not ops and all_ops:
                    text_corpus = f"{inv.get('title', '')} {inv.get('summary', '')} {inv.get('url', '')} {inv.get('final_report', '')}".lower()
                    retro_links = []
                    for op in all_ops:
                        name_clean = op["full_name"].strip().lower()
                        norm_name = op["normalized_name"].strip().lower()
                        if len(name_clean) >= 4 and (name_clean in text_corpus or norm_name in text_corpus):
                            cur.execute("SELECT 1 FROM news_operator_links WHERE news_id = ? AND operator_id = ?", (inv["id"], op["id"]))
                            if not cur.fetchone():
                                link_id = str(uuid.uuid4())
                                cur.execute("""
                                    INSERT INTO news_operator_links (id, news_id, operator_id, role_in_event, notes)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (link_id, inv["id"], op["id"], "Mando / Implicado", "Funcionario implicado detectado retroactivamente"))
                            retro_links.append({
                                "id": op["id"],
                                "full_name": op["full_name"],
                                "sector": op["sector"],
                                "agency": op["agency"],
                                "rank_or_role": op["rank_or_role"],
                                "relation_notes": "Funcionario implicado"
                            })
                    if retro_links:
                        conn.commit()
                        ops = retro_links

                inv["operators"] = ops
                inv["web_domain"] = self._extract_domain(inv.get("url", ""))
                # Do not leak huge markdown report in list response
                inv.pop("final_report", None)
            return invs

    def get_investigation(self, inv_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full investigation including final_report and linked operators."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM news_investigations WHERE id = ?
            """, (inv_id,))
            row = cur.fetchone()
            if not row:
                return None
            inv = dict(row)
            cur.execute("""
                SELECT o.id, o.full_name, o.sector, o.agency, o.rank_or_role, l.role_in_event, l.notes as relation_notes
                FROM news_operator_links l
                JOIN operators o ON l.operator_id = o.id
                WHERE l.news_id = ?
                ORDER BY o.full_name ASC
            """, (inv_id,))
            inv["operators"] = [dict(r) for r in cur.fetchall()]
            inv["web_domain"] = self._extract_domain(inv.get("url", ""))
            return inv

    def generate_dossier_markdown(self, identifier: str) -> str:
        """Generates a complete transparency and accountability dossier in Markdown."""
        op = self.get_operator(identifier)
        if not op:
            return f"No se encontró registro para el operador '{identifier}' en el Directorio."

        incidents = self.get_operator_incidents(op["id"])

        md = []
        md.append(f"# Dossier de Trazabilidad: {op['full_name']}")
        md.append(f"- **ID de Registro**: `{op['id']}`")
        md.append(f"- **Sector**: {op['sector']}")
        md.append(f"- **Institución/Corporación**: {op['agency']}")
        md.append(f"- **Entidad Federativa / Jurisdicción**: {op.get('jurisdiction') or 'Jalisco'}")
        md.append(f"- **Rango / Cargo**: {op['rank_or_role'] or 'No especificado'}")
        md.append(f"- **Periodo en el Cargo / Fechas**: {op.get('tenure_period') or 'En funciones / Periodo en verificación'}")
        md.append(f"- **Placa / Identificador Público**: {op['badge_or_id'] or 'No disponible'}")
        md.append(f"- **Perfil Profesional y Formación**: {op.get('profile_details') or 'Información curricular en proceso de auditoría'}")
        md.append(f"- **Contacto Oficial Institucional**: {op.get('contact_info') or 'Vía Oficial de Atención Ciudadana Institucional'}")
        md.append(f"- **Sede u Oficina Oficial**: {op.get('office_location') or 'Sede Central Institucional'}")
        md.append(f"- **Cadena de Mando (Superiores)**: {op['superiors_chain'] or 'Bajo investigación'}")
        md.append(f"- **Fuerza Operativa / Subordinados**: {op['subordinates_scope'] or 'No especificado'}")
        md.append(f"- **Afiliaciones Políticas**: {op['political_affiliations'] or 'Sin registro partidista formal'}")
        md.append(f"- **Alias**: {op['aliases'] or 'Ninguno'}\n")

        md.append("## Historial de Abusos de Poder y Violaciones Documentadas")
        if not incidents:
            md.append("*No se han registrado incidentes de abuso formalmente validados para este actor.*")
        else:
            for idx, inc in enumerate(incidents, start=1):
                sources = json.loads(inc.get("sources_json") or "[]")
                md.append(f"### {idx}. {inc['incident_type']} ({inc.get('incident_date') or 'Fecha no especificada'})")
                md.append(f"- **Ubicación**: {inc.get('location') or 'No especificada'}")
                md.append(f"- **Estatus de la Investigación**: `{inc['investigation_status']}`")
                md.append(f"- **Detalle de los Hechos**: {inc['description']}")
                if inc.get("victims_summary"):
                    md.append(f"- **Afectados / Víctimas**: {inc['victims_summary']}")
                if sources:
                    md.append(f"- **Fuentes**: {', '.join(sources)}")
                md.append("")

        return "\n".join(md)

    def export_bundle(self, export_dir: Path) -> Dict[str, int]:
        """Exports all operators and incidents into individual JSON and Markdown files for HA distribution."""
        export_dir.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM operators")
            operators = [dict(r) for r in cur.fetchall()]

        count = 0
        for op in operators:
            dossier_md = self.generate_dossier_markdown(op["id"])
            incidents = self.get_operator_incidents(op["id"])
            
            clean_name = op["normalized_name"].replace(" ", "_")
            op_data = {
                "profile": op,
                "incidents": incidents
            }
            # Write JSON
            with open(export_dir / f"{clean_name}.json", "w", encoding="utf-8") as f:
                json.dump(op_data, f, ensure_ascii=False, indent=2)
            # Write Markdown
            with open(export_dir / f"{clean_name}.md", "w", encoding="utf-8") as f:
                f.write(dossier_md)
            count += 1

        return {"exported_operators": count}
