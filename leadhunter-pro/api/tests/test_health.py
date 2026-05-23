"""Tests del endpoint /health (sin auth)."""
import pytest
from fastapi.testclient import TestClient


def _make_fake_supabase(ok: bool):
    """Devuelve un cliente Supabase mock que simula una BD viva o caída."""
    class _Exec:
        def execute(self):
            if not ok:
                raise RuntimeError("boom")
            return type("R", (), {"data": []})()

    class _Q:
        def select(self, *_):
            return self

        def limit(self, *_):
            return _Exec()

    class _Client:
        def table(self, *_):
            return _Q()

    return _Client()


@pytest.fixture
def client():
    """TestClient con la dependencia get_supabase override-eable por test."""
    from main import app
    return TestClient(app)


def test_root_returns_metadata(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "cazador-api"
    assert body["docs"] == "/docs"


def test_health_db_ok_when_supabase_responds(client):
    """Si Supabase responde, /health devuelve db=ok."""
    from db import get_supabase
    from main import app

    app.dependency_overrides[get_supabase] = lambda: _make_fake_supabase(ok=True)
    try:
        res = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    body = res.json()
    assert body["db"] == "ok"
    assert body["schema_version"] == "2.0.0"


def test_health_db_down_when_supabase_raises(client):
    from db import get_supabase
    from main import app

    app.dependency_overrides[get_supabase] = lambda: _make_fake_supabase(ok=False)
    try:
        res = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    body = res.json()
    assert body["db"] == "down"
    assert body["status"] == "degraded"


def test_sources_endpoint_returns_list(client):
    res = client.get("/health/sources")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
