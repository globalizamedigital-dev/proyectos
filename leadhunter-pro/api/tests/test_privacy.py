"""Tests de los endpoints GDPR (/privacy/export, /privacy/erase, /unsubscribe)."""
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _fake_supabase(
    leads: list[dict[str, Any]] | None = None,
    sup: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    tenant_id: str | None = "00000000-0000-0000-0000-000000000001",
):
    """Mock Supabase client suficiente para los endpoints privacy."""
    leads = leads or []
    sup = sup or []
    events = events or []
    deleted: dict[str, list] = {"leads": [], "suppression": []}

    class _Q:
        def __init__(self, table_name: str):
            self.table_name = table_name
            self._filters: list[tuple[str, str, Any]] = []
            self._payload: Any = None
            self._op: str = "select"

        # Encadenables
        def select(self, *_):
            self._op = "select"
            return self

        def insert(self, payload):
            self._op = "insert"
            self._payload = payload
            return self

        def delete(self):
            self._op = "delete"
            return self

        def upsert(self, payload):
            self._op = "upsert"
            self._payload = payload
            return self

        def eq(self, col, val):
            self._filters.append(("eq", col, val))
            return self

        def in_(self, col, vals):
            self._filters.append(("in", col, list(vals)))
            return self

        def limit(self, *_):
            return self

        def maybe_single(self):
            return self

        # Terminales
        def execute(self):
            if self.table_name == "tenants" and self._op == "select":
                return MagicMock(data={"id": tenant_id} if tenant_id else None)
            if self.table_name == "leads":
                if self._op == "select":
                    rows = [l for l in leads if _matches(l, self._filters)]
                    return MagicMock(data=rows)
                if self._op == "delete":
                    for f in self._filters:
                        if f[0] == "in" and f[1] == "id":
                            deleted["leads"].extend(f[2])
                    return MagicMock(data=[])
            if self.table_name == "outreach_events":
                rows = [e for e in events if _matches(e, self._filters)]
                return MagicMock(data=rows)
            if self.table_name == "suppression":
                if self._op == "select":
                    rows = [s for s in sup if _matches(s, self._filters)]
                    return MagicMock(data=rows)
                if self._op in ("delete", "upsert", "insert"):
                    if self._op == "delete":
                        deleted["suppression"].append(self._filters)
                    return MagicMock(data=[])
            if self.table_name == "usage_events":
                return MagicMock(data=[])
            return MagicMock(data=[])

    def _matches(row, filters):
        for op, col, val in filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "in" and row.get(col) not in val:
                return False
        return True

    class _Client:
        def table(self, name):
            return _Q(name)

    client = _Client()
    client._deleted = deleted  # type: ignore[attr-defined]
    return client


def test_export_requires_auth(client):
    res = client.post("/privacy/export", json={"kind": "email", "value": "x@y.com"})
    assert res.status_code == 401


def test_export_returns_leads_for_email(client):
    from db import get_supabase
    from main import app

    sb = _fake_supabase(
        leads=[
            {"id": "lead-1", "email_principal": "test@globalizame.com", "razon_social": "Demo SL"},
        ],
        sup=[{"channel": "email", "identifier": "test@globalizame.com", "reason": "manual"}],
    )
    app.dependency_overrides[get_supabase] = lambda: sb
    try:
        res = client.post(
            "/privacy/export",
            json={"kind": "email", "value": "TEST@globalizame.com"},
            headers={"Authorization": "Dev mario"},
        )
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    body = res.json()
    assert body["subject"] == {"kind": "email", "value": "test@globalizame.com"}
    assert body["counts"]["leads"] == 1
    assert body["counts"]["suppression"] == 1


def test_erase_removes_leads_and_suppression(client):
    from db import get_supabase
    from main import app

    sb = _fake_supabase(
        leads=[{"id": "lead-99", "email_principal": "borrame@x.com"}],
        sup=[{"channel": "email", "identifier": "borrame@x.com", "reason": "manual"}],
    )
    app.dependency_overrides[get_supabase] = lambda: sb
    try:
        res = client.request(
            "DELETE",
            "/privacy/erase",
            json={"kind": "email", "value": "borrame@x.com"},
            headers={"Authorization": "Dev mario"},
        )
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    body = res.json()
    assert body["erased"] is True
    assert body["deleted"] == {"leads": 1, "suppression": 1}
    # Confirmamos que el delete se invocó con el lead-99
    assert "lead-99" in sb._deleted["leads"]  # type: ignore[attr-defined]


def test_unsubscribe_with_invalid_token_returns_400(client):
    res = client.get("/unsubscribe?token=notvalid_token_xxxxxxxx")
    assert res.status_code == 400


def test_unsubscribe_full_roundtrip(client):
    """Generamos un token con la misma función del módulo y lo verificamos."""
    from db import get_supabase
    from main import app
    from routes.privacy import _sign_token, _unsubscribe_secret
    from settings import get_settings

    sb = _fake_supabase()
    app.dependency_overrides[get_supabase] = lambda: sb
    try:
        token = _sign_token("baja@x.com", _unsubscribe_secret(get_settings()))
        res = client.get(f"/unsubscribe?token={token}")
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    assert "baja@x.com" in res.text
    assert "globalizame" in res.text.lower()


def test_token_normalizes_to_lowercase():
    from routes.privacy import _sign_token, _verify_token

    secret = "test-secret"
    token = _sign_token("Foo@Bar.com", secret)
    assert _verify_token(token, secret) == "foo@bar.com"


def test_token_tampering_is_detected():
    from routes.privacy import _sign_token, _verify_token

    secret = "test-secret"
    token = _sign_token("real@x.com", secret)
    # Manipulamos el token (cambiamos un byte)
    tampered = token[:-2] + ("zz" if token[-2:] != "zz" else "aa")
    assert _verify_token(tampered, secret) is None

    # Otro secret no valida
    assert _verify_token(token, "other-secret") is None
