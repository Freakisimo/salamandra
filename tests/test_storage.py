import pytest
import tempfile
import json
from pathlib import Path
from src.storage.ledger import AuditLedger, GENESIS_HASH
from src.storage.person_directory import PersonDirectory

def test_ledger_append_and_verify():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        
        valid, _ = ledger.verify_integrity()
        assert valid is True
        
        # Append block 0
        b0 = ledger.append_entry("ACTION_A", {"key": "val1"})
        assert b0["index"] == 0
        assert b0["prev_hash"] == GENESIS_HASH
        
        # Append block 1
        b1 = ledger.append_entry("ACTION_B", {"key": "val2"})
        assert b1["index"] == 1
        assert b1["prev_hash"] == b0["hash"]
        
        valid, msg = ledger.verify_integrity()
        assert valid is True
        assert "2 blocks" in msg

def test_ledger_tamper_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        
        ledger.append_entry("ACTION_A", {"data": "authentic"})
        ledger.append_entry("ACTION_B", {"data": "authentic_2"})
        
        # Tamper with file
        lines = []
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]
            
        lines[0]["payload"]["data"] = "tampered"
        with open(ledger_path, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")
                
        valid, msg = ledger.verify_integrity()
        assert valid is False
        assert "mismatch" in msg.lower()

def test_person_directory_crud_and_dossier():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        dir_mgr = PersonDirectory(db_path, ledger)
        
        # Upsert operator with transparency details
        op = dir_mgr.upsert_operator(
            full_name="Fiscal General Rogelio Mendez",
            sector="Ministerial/Fiscalía",
            agency="Fiscalía General del Estado",
            rank_or_role="Fiscal Especializado",
            superiors_chain="Fiscal General Titular",
            subordinates_scope="Ministerios Públicos de Delitos Patrimoniales",
            tenure_period="2022 - 2026",
            profile_details="Maestría en Ciencias Penales, Cédula 9876543",
            contact_info="fiscalia.contacto@estado.gob.mx",
            office_location="Edificio Central de Fiscalías, Piso 4"
        )
        assert op["id"] is not None
        assert op["tenure_period"] == "2022 - 2026"
        assert op["profile_details"] == "Maestría en Ciencias Penales, Cédula 9876543"
        assert op["contact_info"] == "fiscalia.contacto@estado.gob.mx"
        assert op["office_location"] == "Edificio Central de Fiscalías, Piso 4"
        
        # Log incident
        inc = dir_mgr.log_abuse_incident(
            operator_name_or_id="Fiscal General Rogelio Mendez",
            incident_type="Fabricación de pruebas",
            description="Sembrado de armas en cateo ilegal a activistas de derechos humanos",
            sources=["https://informe-ddhh.org/caso-1"]
        )
        assert inc["incident_id"] is not None
        
        # Generate markdown dossier
        md = dir_mgr.generate_dossier_markdown(op["id"])
        assert "Fiscal General Rogelio Mendez" in md
        assert "Fabricación de pruebas" in md
        assert "Cadena de Mando" in md
        assert "2022 - 2026" in md
        assert "Maestría en Ciencias Penales" in md
        assert "fiscalia.contacto@estado.gob.mx" in md
        assert "Edificio Central de Fiscalías, Piso 4" in md
        
        # Export bundle
        export_dir = Path(tmpdir) / "export"
        res = dir_mgr.export_bundle(export_dir)
        assert res["exported_operators"] == 1
        exported_files = list(export_dir.glob("*"))
        assert len(exported_files) == 2 # 1 JSON and 1 MD

def test_investigation_persistence_and_retrieval():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        dir_mgr = PersonDirectory(db_path, ledger)

        # Pre-register an operator
        op = dir_mgr.upsert_operator(
            full_name="Comandante Roberto Garza",
            sector="Policial",
            agency="Secretaría de Seguridad",
            rank_or_role="Mando Operativo",
            tenure_period="2023 - 2026"
        )

        # Save investigation mentioning the operator
        saved = dir_mgr.save_investigation(
            title="Desalojo en Eje Central",
            query_or_url="https://noticias.mx/desalojo-eje-central",
            final_report="# 1. Resumen Ejecutivo\nEl Comandante Roberto Garza dirigió el operativo de desalojo violento.",
            summary="Desalojo violento por parte de mandos policiales."
        )
        assert saved["id"] is not None
        assert saved["title"] == "Desalojo en Eje Central"
        assert len(saved["operators"]) == 1
        assert saved["operators"][0]["full_name"] == "Comandante Roberto Garza"

        # List investigations
        invs = dir_mgr.list_investigations()
        assert len(invs) == 1
        assert invs[0]["id"] == saved["id"]
        assert invs[0]["url"] == "https://noticias.mx/desalojo-eje-central"
        assert len(invs[0]["operators"]) == 1
        assert invs[0]["operators"][0]["full_name"] == "Comandante Roberto Garza"

        # Get single investigation
        single = dir_mgr.get_investigation(saved["id"])
        assert single is not None
        assert "# 1. Resumen Ejecutivo" in single["final_report"]
        assert len(single["operators"]) == 1
        assert single["operators"][0]["full_name"] == "Comandante Roberto Garza"

        # Verify ledger has LOG_INVESTIGATION action
        entries = ledger.read_all_entries()
        assert any(e["action"] == "LOG_INVESTIGATION" for e in entries)

def test_operator_incident_counts_and_search_filters():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        dir_mgr = PersonDirectory(db_path, ledger)

        # Operator 1: Policial with 1 incident
        op1 = dir_mgr.upsert_operator(
            full_name="Comandante Arturo Velez",
            sector="Policial",
            agency="Secretaría de Seguridad",
            rank_or_role="Comandante de Sector"
        )
        dir_mgr.log_abuse_incident(
            operator_name_or_id="Comandante Arturo Velez",
            incident_type="Detención arbitraria",
            description="Detuvo sin orden judicial a reporteros"
        )

        # Operator 2: Judicial without incidents
        op2 = dir_mgr.upsert_operator(
            full_name="Jueza Beatriz Paredes",
            sector="Judicial",
            agency="Tribunal de Justicia",
            rank_or_role="Jueza Civil"
        )

        # Search with count
        results = dir_mgr.search_operators(query="")
        assert len(results) == 2
        # Op 1 should be first because incidents_count = 1 vs 0
        assert results[0]["full_name"] == "Comandante Arturo Velez"
        assert results[0]["incidents_count"] == 1
        assert results[1]["incidents_count"] == 0

        # Filter by sector
        police_res = dir_mgr.search_operators(sector="policial")
        assert len(police_res) == 1
        assert police_res[0]["full_name"] == "Comandante Arturo Velez"

        # Filter by query
        search_res = dir_mgr.search_operators(query="Beatriz")
        assert len(search_res) == 1
        assert search_res[0]["full_name"] == "Jueza Beatriz Paredes"

        # Get structured dossier
        dossier = dir_mgr.get_operator_dossier(op1["id"])
        assert dossier is not None
        assert dossier["incidents_count"] == 1
        assert len(dossier["incidents"]) == 1
        assert "Detención arbitraria" in dossier["dossier_markdown"]

def test_jurisdiction_and_directory_filter_options():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        dir_mgr = PersonDirectory(db_path, ledger)

        # 1. Add operator with explicit jurisdiction
        op_jal = dir_mgr.upsert_operator(
            full_name="Fiscal Regional Altos",
            sector="Fiscalía",
            agency="Fiscalía General del Estado de Jalisco",
            rank_or_role="Fiscal Regional",
            jurisdiction="Jalisco"
        )
        assert op_jal["jurisdiction"] == "Jalisco"

        # 2. Add operator with auto-inferred jurisdiction from agency
        op_cdmx = dir_mgr.upsert_operator(
            full_name="Mando Operativo SSC",
            sector="Policial",
            agency="Secretaría de Seguridad Ciudadana de la Ciudad de México",
            rank_or_role="Director de Sector"
        )
        assert op_cdmx["jurisdiction"] == "Ciudad de México"

        # Add abuse incident to Jalisco operator
        dir_mgr.log_abuse_incident(
            operator_name_or_id="Fiscal Regional Altos",
            incident_type="Cohecho y dilación procesal",
            description="Exigió dádivas para dar trámite a carpetas"
        )

        # 3. Test filter options
        filter_opts = dir_mgr.get_directory_filter_options()
        assert "Jalisco" in filter_opts["jurisdictions"]
        assert "Ciudad de México" in filter_opts["jurisdictions"]
        assert "Fiscalía General del Estado de Jalisco" in filter_opts["agencies"]
        assert len(filter_opts["statuses"]) == 4

        # 4. Filter by jurisdiction
        jal_ops = dir_mgr.search_operators(jurisdiction="Jalisco")
        assert len(jal_ops) == 1
        assert jal_ops[0]["full_name"] == "Fiscal Regional Altos"

        # 5. Filter by status: con_reportes
        reported_ops = dir_mgr.search_operators(status="con_reportes")
        assert len(reported_ops) == 1
        assert reported_ops[0]["full_name"] == "Fiscal Regional Altos"

        # 6. Filter by status: sin_reportes
        clean_ops = dir_mgr.search_operators(status="sin_reportes")
        assert len(clean_ops) == 1
        assert clean_ops[0]["full_name"] == "Mando Operativo SSC"

def test_investigation_date_filtering_and_domain_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        dir_mgr = PersonDirectory(db_path, ledger)

        # Save investigation from domain
        inv1 = dir_mgr.save_investigation(
            title="Investigación de Medios",
            query_or_url="https://elpais.com/mexico/2026/reportaje-policial.html",
            final_report="Reporte objetivo sin sesgos",
            summary="Resumen de hechos"
        )
        assert inv1["web_domain"] == "elpais.com"

        # List investigations with domain
        invs = dir_mgr.list_investigations()
        assert len(invs) == 1
        assert invs[0]["web_domain"] == "elpais.com"

        # Query filter
        matched = dir_mgr.list_investigations(query="elpais")
        assert len(matched) == 1
        unmatched = dir_mgr.list_investigations(query="inexistente")
        assert len(unmatched) == 0
