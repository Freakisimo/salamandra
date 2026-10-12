import pytest
from starlette.testclient import TestClient
from src.agents.orchestrator import app

def test_web_ui_endpoints():
    with TestClient(app) as client:
        # 1. Test Home UI HTML & Navigation Layout
        res_home = client.get("/")
        assert res_home.status_code == 200
        assert "SALAMANDRA" in res_home.text
        assert "news-url-input" in res_home.text
        assert "analyze-btn" in res_home.text
        assert "app-navbar" in res_home.text
        assert "view-new-query" in res_home.text
        assert "view-history" in res_home.text
        assert "view-directory" in res_home.text
        assert "view-report" in res_home.text
        assert "view-ledger" in res_home.text

        # 2. Test Static CSS
        res_css = client.get("/static/css/styles.css")
        assert res_css.status_code == 200
        assert "--accent-emerald" in res_css.text
        assert ".app-navbar" in res_css.text

        # 3. Test Static JS
        res_js = client.get("/static/js/app.js")
        assert res_js.status_code == 200
        assert "news-investigate-form" in res_js.text
        assert "loadDirectoryFilters" in res_js.text

        # 4. Test API Directory
        res_dir = client.get("/api/directory")
        assert res_dir.status_code == 200
        assert isinstance(res_dir.json(), list)

        # 5. Test API Directory Filter Options
        res_filters = client.get("/api/directory/filters")
        assert res_filters.status_code == 200
        filter_data = res_filters.json()
        assert "jurisdictions" in filter_data
        assert "agencies" in filter_data
        assert "statuses" in filter_data

        # 6. Test API Ledger
        res_ledger = client.get("/api/ledger")
        assert res_ledger.status_code == 200
        data = res_ledger.json()
        assert "valid" in data
        assert "entries" in data

        # 7. Test API Investigate validation
        res_empty = client.post("/api/investigate", json={"query": "   "})
        assert res_empty.status_code == 400
        assert "error" in res_empty.json()

        # 8. Test API Directory search & jurisdiction/sector/status filter
        res_dir_filter = client.get("/api/directory?jurisdiction=todos&agency=todos&status=todos&sector=policial&q=test")
        assert res_dir_filter.status_code == 200
        assert isinstance(res_dir_filter.json(), list)

        # 9. Test API Investigations list with date filter params
        res_invs = client.get("/api/investigations?start_date=2026-01-01&end_date=2026-12-31&q=test")
        assert res_invs.status_code == 200
        assert isinstance(res_invs.json(), list)

        # 10. Test API Investigation not found
        res_inv_404 = client.get("/api/investigations/non-existent-id")
        assert res_inv_404.status_code == 404

        # 11. Test API Operator Dossier not found
        res_op_404 = client.get("/api/directory/non-existent-id")
        assert res_op_404.status_code == 404

def test_extract_text_from_a2a_response_formats():
    from src.core.a2a_client import extract_text_from_a2a_response

    # Test artifact format
    art_payload = {
        "jsonrpc": "2.0",
        "result": {
            "artifacts": [{"parts": [{"text": "Dossier verificado"}]}]
        }
    }
    assert extract_text_from_a2a_response(art_payload) == "Dossier verificado"

    # Test ROLE_AGENT history format
    hist_payload = {
        "jsonrpc": "2.0",
        "result": {
            "history": [
                {"role": "ROLE_USER", "parts": [{"text": "hola"}]},
                {"role": "ROLE_AGENT", "parts": [{"text": "reporte final"}]}
            ]
        }
    }
    assert extract_text_from_a2a_response(hist_payload) == "reporte final"

    # Test error format
    err_payload = {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Fallo de conexión"}
    }
    assert "Fallo de conexión" in extract_text_from_a2a_response(err_payload)
