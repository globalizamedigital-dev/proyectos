"""
Tests del wrapper fetch_client.

No salimos a Internet (los tests reales contra DDG/AEPD se hacen en smoke).
Aquí solo verificamos: 1) que las tres funciones existen con la firma
correcta; 2) que el fallback a urllib funciona cuando se desactiva
Scrapling; 3) que las funciones devuelven la tupla `(int, str)`
esperada por todos los adapters.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_client  # noqa: E402


class TestFetchClientAPI(unittest.TestCase):
    def test_three_modes_callable(self):
        for fn_name in ("fetch_plain", "fetch_stealthy", "fetch_dynamic"):
            self.assertTrue(callable(getattr(fetch_client, fn_name)))

    def test_response_tuple_shape(self):
        """Las tres funciones deben devolver (int, str) — contrato heredado de http_get."""
        # Mockeamos http_get para no salir a red.
        with patch.object(fetch_client, "http_get", return_value=(200, "ok-body")):
            status, body = fetch_client.fetch_plain("https://example.test")
            self.assertEqual(status, 200)
            self.assertEqual(body, "ok-body")
            self.assertIsInstance(status, int)
            self.assertIsInstance(body, str)

    def test_response_to_tuple_decodes_bytes(self):
        """`_response_to_tuple` debe decodificar el body cuando viene en bytes."""
        class _FakeResp:
            status = 200
            body = b"hola mundo \xc3\xa1"
            encoding = "utf-8"
        status, body = fetch_client._response_to_tuple(_FakeResp())
        self.assertEqual(status, 200)
        self.assertEqual(body, "hola mundo á")

    def test_response_to_tuple_handles_error(self):
        """Si la respuesta lanza al acceder, devolvemos status negativo (no -1 ni 0)."""
        class _Broken:
            @property
            def body(self):
                raise RuntimeError("boom")
            status = 200
            encoding = "utf-8"
        status, body = fetch_client._response_to_tuple(_Broken())
        self.assertEqual(status, -2)
        self.assertIn("RuntimeError", body)


class TestFeatureFlagFallback(unittest.TestCase):
    """Con LEADHUNTER_USE_SCRAPLING=false, los tres modos colapsan a urllib."""

    def setUp(self):
        # Reset del cache de detección para forzar recheck.
        fetch_client._scrapling_available = None
        fetch_client._dynamic_available = None
        self._original_flag = fetch_client._USE_SCRAPLING

    def tearDown(self):
        fetch_client._USE_SCRAPLING = self._original_flag
        fetch_client._scrapling_available = None
        fetch_client._dynamic_available = None

    def test_disabled_flag_routes_stealthy_to_plain(self):
        fetch_client._USE_SCRAPLING = False
        with patch.object(fetch_client, "http_get", return_value=(200, "plain-body")) as mock_get:
            status, body = fetch_client.fetch_stealthy("https://example.test")
        self.assertEqual((status, body), (200, "plain-body"))
        mock_get.assert_called_once()

    def test_disabled_flag_routes_dynamic_to_plain(self):
        fetch_client._USE_SCRAPLING = False
        with patch.object(fetch_client, "http_get", return_value=(200, "plain-body")):
            status, body = fetch_client.fetch_dynamic("https://example.test")
        self.assertEqual(status, 200)


class TestFetchPlainPassthrough(unittest.TestCase):
    """fetch_plain debe ser delegación pura a http_get sin tocar Scrapling."""

    def test_signature_passthrough(self):
        with patch.object(fetch_client, "http_get", return_value=(418, "I am a teapot")) as mock_get:
            status, body = fetch_client.fetch_plain(
                "https://example.test",
                headers={"X-Test": "1"},
                timeout=5,
                retries=2,
                rate_limit=0.5,
            )
        self.assertEqual(status, 418)
        self.assertEqual(body, "I am a teapot")
        mock_get.assert_called_once_with(
            "https://example.test",
            headers={"X-Test": "1"},
            timeout=5,
            retries=2,
            rate_limit=0.5,
        )


if __name__ == "__main__":
    unittest.main()
