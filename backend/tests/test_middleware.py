import uuid


def test_request_id_is_minted_and_echoed(client):
    res = client.get("/api/health")
    assert uuid.UUID(res.headers["X-Request-ID"])  # valid UUID


def test_valid_incoming_request_id_is_kept(client):
    incoming = str(uuid.uuid4())
    res = client.get("/api/health", headers={"X-Request-ID": incoming})
    assert res.headers["X-Request-ID"] == incoming


def test_invalid_incoming_request_id_is_replaced(client):
    res = client.get("/api/health", headers={"X-Request-ID": "not-a-uuid\ninjected"})
    assert res.headers["X-Request-ID"] != "not-a-uuid\ninjected"
    assert uuid.UUID(res.headers["X-Request-ID"])


def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"


def test_unhandled_errors_return_generic_500(client, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import articles as articles_router

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(articles_router.article_service, "stats", boom)
    # The default TestClient re-raises server exceptions; here we want to see the HTTP response instead
    with TestClient(app, raise_server_exceptions=False) as quiet_client:
        res = quiet_client.get("/api/articles/stats")
    assert res.status_code == 500
    assert res.json() == {"detail": "Internal server error"}
    assert "secret" not in res.text


def test_unknown_api_route_is_json_404_not_frontend(client):
    from app.main import FRONTEND_DIST

    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    if FRONTEND_DIST.exists():  # the SPA catch-all is only mounted when the frontend is built
        assert res.json() == {"detail": "Not found"}


def test_health_reports_database_engine(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"] in {"sqlite", "postgresql"}
