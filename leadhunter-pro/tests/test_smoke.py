"""
test_smoke.py — Suite de pruebas de humo de LeadHunter Pro.

Solo stdlib (unittest). No requiere acceso a red: toda la lógica probada es
offline. Las bases de datos SQLite se crean en un directorio temporal aislado
mediante la variable de entorno HOME, de modo que NO tocan los datos reales
del usuario.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest tests.test_smoke -v
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# --- Aislamiento: redirigir HOME a un directorio temporal ANTES de importar ---
# Los módulos calculan rutas de BD/cache a partir de Path.home() en tiempo de
# import, así que esto debe hacerse antes de importar los módulos del proyecto.
_TMP_HOME = tempfile.mkdtemp(prefix="leadhunter_test_home_")
os.environ["HOME"] = _TMP_HOME
os.environ.pop("LEADHUNTER_ENV", None)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import _common  # noqa: E402
import config as config_mod  # noqa: E402
import lead_scorer  # noqa: E402
import leads_db  # noqa: E402
import outreach  # noqa: E402
import suppression  # noqa: E402


# ---------------------------------------------------------------------------
# NIF validation

class TestNifValidation(unittest.TestCase):
    def test_valid_cif(self):
        self.assertTrue(_common.is_valid_nif("B12345678"))

    def test_valid_dni(self):
        self.assertTrue(_common.is_valid_nif("12345678Z"))

    def test_valid_nie(self):
        self.assertTrue(_common.is_valid_nif("X1234567L"))

    def test_invalid_empty(self):
        self.assertFalse(_common.is_valid_nif(""))

    def test_invalid_garbage(self):
        self.assertFalse(_common.is_valid_nif("NOT-A-NIF"))

    def test_invalid_too_short(self):
        self.assertFalse(_common.is_valid_nif("B123"))

    def test_normalize_nif_strips_and_uppercases(self):
        self.assertEqual(_common.normalize_nif(" b-1234 5678 "), "B12345678")


# ---------------------------------------------------------------------------
# Sector resolution

class TestSectorResolution(unittest.TestCase):
    def test_resolve_known_sector(self):
        result = _common.resolve_sector("asesoría fiscal")
        self.assertIn(result["matched_via"], ("exact", "alias", "fuzzy"))
        self.assertIsInstance(result["cnae"], list)

    def test_resolve_cnae_code(self):
        result = _common.resolve_sector("6920")
        self.assertEqual(result["matched_via"], "cnae")
        self.assertIn("6920", result["cnae"])

    def test_resolve_unknown_sector(self):
        result = _common.resolve_sector("xyzqwerty no existe sector")
        self.assertEqual(result["matched_via"], "none")
        self.assertEqual(result["cnae"], [])


# ---------------------------------------------------------------------------
# Email permutations

class TestEmailPermutations(unittest.TestCase):
    def test_two_surnames_generates_candidates(self):
        perms = _common.generar_permutaciones_email(
            "José", "García", "López", "empresa.es")
        self.assertTrue(perms)
        self.assertIn("jose.garcia.lopez@empresa.es", perms)
        self.assertIn("j.garcia@empresa.es", perms)

    def test_permutations_are_deduplicated(self):
        perms = _common.generar_permutaciones_email(
            "Ana", "Ruiz", None, "test.com")
        self.assertEqual(len(perms), len(set(perms)))

    def test_no_domain_returns_empty(self):
        self.assertEqual(
            _common.generar_permutaciones_email("Ana", "Ruiz", None, ""), [])

    def test_parse_nombre_partes(self):
        partes = _common.parse_nombre_partes("José García López")
        self.assertEqual(partes["nombre"], "jose")
        self.assertEqual(partes["apellido1"], "garcia")
        self.assertEqual(partes["apellido2"], "lopez")


# ---------------------------------------------------------------------------
# Lead scoring math

class TestLeadScoring(unittest.TestCase):
    def test_empty_lead_scores_low(self):
        result = lead_scorer.score({"razonSocial": "Vacía S.L."})
        self.assertEqual(result["grade"], "D")
        self.assertLess(result["score"], 25)

    def test_rich_lead_scores_high(self):
        lead = {
            "razonSocial": "Completa S.L.",
            "domain": {"resolved": "completa.es"},
            "emails": [{"email": "ceo@completa.es", "confidence": "verified"}],
            "decisionMakers": [{"name": "Juan Pérez", "role": "CEO"}],
            "phones": ["+34 911 222 333"],
            "compliance": {"dpoRegistered": True},
        }
        result = lead_scorer.score(lead)
        self.assertGreaterEqual(result["score"], 75)
        self.assertEqual(result["grade"], "A")

    def test_score_is_capped_at_100(self):
        lead = {
            "razonSocial": "Tope S.L.",
            "domain": {"resolved": "tope.es"},
            "emails": [{"email": "x@tope.es", "confidence": "verified"}],
            "decisionMakers": [{"name": "X"}],
            "phones": ["1"],
            "compliance": {"dpoRegistered": True},
            "publicContracts": [{"id": 1}],
            "subsidies": [{"id": 1}],
        }
        result = lead_scorer.score(lead)
        self.assertLessEqual(result["score"], 100)

    def test_verified_email_not_double_counted(self):
        # Un email verificado puntúa por has_verified_email (25), no además
        # por has_email (15). Sin decisor/teléfono el total debe ser 20+25=45.
        lead = {
            "razonSocial": "X S.L.",
            "domain": {"resolved": "x.es"},
            "emails": [{"email": "a@x.es", "confidence": "verified"}],
        }
        result = lead_scorer.score(lead)
        self.assertEqual(result["score"], 45)


# ---------------------------------------------------------------------------
# Suppression list

class TestSuppression(unittest.TestCase):
    def setUp(self):
        # BD limpia por test
        if suppression.DB_PATH.exists():
            suppression.DB_PATH.unlink()

    def test_add_and_check_email(self):
        suppression.add_suppression(email="baja@ejemplo.com")
        self.assertTrue(suppression.is_suppressed(email="baja@ejemplo.com"))

    def test_not_suppressed_by_default(self):
        self.assertFalse(suppression.is_suppressed(email="libre@ejemplo.com"))

    def test_add_is_idempotent(self):
        id1 = suppression.add_suppression(email="dup@ejemplo.com")
        id2 = suppression.add_suppression(email="dup@ejemplo.com")
        self.assertEqual(id1, id2)

    def test_domain_suppression_blocks_email(self):
        suppression.add_suppression(domain="bloqueado.com")
        self.assertTrue(
            suppression.is_suppressed(email="cualquiera@bloqueado.com"))

    def test_nif_suppression(self):
        suppression.add_suppression(nif="B12345678")
        self.assertTrue(suppression.is_suppressed(nif="b12345678"))

    def test_remove_suppression(self):
        suppression.add_suppression(email="quitar@ejemplo.com")
        removed = suppression.remove_suppression("quitar@ejemplo.com")
        self.assertEqual(removed, 1)
        self.assertFalse(suppression.is_suppressed(email="quitar@ejemplo.com"))

    def test_list_suppressions(self):
        suppression.add_suppression(email="uno@ejemplo.com")
        suppression.add_suppression(email="dos@ejemplo.com")
        entries = suppression.list_suppressions()
        self.assertEqual(len(entries), 2)

    def test_email_is_case_insensitive(self):
        suppression.add_suppression(email="Mixed@Case.Com")
        self.assertTrue(suppression.is_suppressed(email="mixed@case.com"))


# ---------------------------------------------------------------------------
# Leads DB

class TestLeadsDB(unittest.TestCase):
    def setUp(self):
        if leads_db.DB_PATH.exists():
            leads_db.DB_PATH.unlink()

    def test_upsert_and_get_by_nif(self):
        lead = {"razonSocial": "Demo S.L.", "nif": "B11111111",
                "domain": {"resolved": "demo.es"}}
        lead_id = leads_db.upsert_lead(lead)
        self.assertGreater(lead_id, 0)
        fetched = leads_db.get_lead(nif="B11111111")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["razonSocial"], "Demo S.L.")

    def test_dedup_by_nif(self):
        leads_db.upsert_lead({"razonSocial": "A S.L.", "nif": "B22222222"})
        leads_db.upsert_lead({"razonSocial": "A S.L. actualizada",
                              "nif": "B22222222"})
        self.assertEqual(leads_db.count_leads()["total"], 1)

    def test_dedup_by_razon_social_and_domain(self):
        leads_db.upsert_lead({"razonSocial": "Sin NIF S.L.",
                              "domain": {"resolved": "sinnif.es"}})
        leads_db.upsert_lead({"razonSocial": "Sin NIF S.L.",
                              "domain": {"resolved": "sinnif.es"}})
        self.assertEqual(leads_db.count_leads()["total"], 1)

    def test_distinct_leads_not_merged(self):
        leads_db.upsert_lead({"razonSocial": "Uno S.L.", "nif": "B33333333"})
        leads_db.upsert_lead({"razonSocial": "Dos S.L.", "nif": "B44444444"})
        self.assertEqual(leads_db.count_leads()["total"], 2)

    def test_query_min_score(self):
        leads_db.upsert_lead({"razonSocial": "Alta S.L.", "nif": "B55555555",
                              "score": {"score": 80}})
        leads_db.upsert_lead({"razonSocial": "Baja S.L.", "nif": "B66666666",
                              "score": {"score": 10}})
        high = leads_db.query_leads(min_score=50)
        self.assertEqual(len(high), 1)

    def test_update_outreach_status(self):
        lead_id = leads_db.upsert_lead({"razonSocial": "Estado S.L.",
                                        "nif": "B77777777"})
        self.assertTrue(leads_db.update_outreach_status(lead_id, "contacted"))
        counts = leads_db.count_leads()
        self.assertEqual(counts["by_status"].get("contacted"), 1)

    def test_upsert_lead_without_data_returns_zero(self):
        self.assertEqual(leads_db.upsert_lead({}), 0)


# ---------------------------------------------------------------------------
# Template filling

class TestTemplateFilling(unittest.TestCase):
    def test_simple_variable_substitution(self):
        out = outreach.fill_template("Hola {nombre}", {"nombre": "Ana"})
        self.assertEqual(out, "Hola Ana")

    def test_double_brace_substitution(self):
        out = outreach.fill_template("Hola {{nombre}}", {"nombre": "Ana"})
        self.assertEqual(out, "Hola Ana")

    def test_conditional_true_keeps_content(self):
        out = outreach.fill_template(
            "X{if ciudad} en {ciudad}{endif}Y", {"ciudad": "Madrid"})
        self.assertEqual(out, "X en MadridY")

    def test_conditional_false_drops_content(self):
        out = outreach.fill_template(
            "X{if ciudad} en {ciudad}{endif}Y", {"ciudad": ""})
        self.assertEqual(out, "XY")

    def test_none_value_renders_empty(self):
        out = outreach.fill_template("[{x}]", {"x": None})
        self.assertEqual(out, "[]")

    def test_prepare_email_fills_enlace_baja(self):
        lead = {
            "razonSocial": "Plantilla S.L.",
            "emails": [{"email": "info@plantilla.es"}],
        }
        prepared = outreach.prepare_email(
            lead, "email_cold_es.txt", from_email="ventas@miempresa.es")
        self.assertIsNotNone(prepared)
        self.assertIn("ventas@miempresa.es", prepared["body"])
        # El placeholder debe haberse resuelto
        self.assertNotIn("{enlace_baja}", prepared["body"])


# ---------------------------------------------------------------------------
# Rate limiter timing

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        _common.RateLimiter.reset()

    def test_first_call_does_not_block(self):
        start = time.monotonic()
        _common.RateLimiter.wait("host-a.example", 0.3)
        self.assertLess(time.monotonic() - start, 0.1)

    def test_second_call_blocks(self):
        _common.RateLimiter.wait("host-b.example", 0.3)
        start = time.monotonic()
        _common.RateLimiter.wait("host-b.example", 0.3)
        elapsed = time.monotonic() - start
        self.assertGreaterEqual(elapsed, 0.25)

    def test_different_hosts_independent(self):
        _common.RateLimiter.wait("host-c.example", 0.5)
        start = time.monotonic()
        _common.RateLimiter.wait("host-d.example", 0.5)
        self.assertLess(time.monotonic() - start, 0.1)

    def test_zero_interval_never_blocks(self):
        _common.RateLimiter.wait("host-e.example", 0)
        start = time.monotonic()
        _common.RateLimiter.wait("host-e.example", 0)
        self.assertLess(time.monotonic() - start, 0.05)


# ---------------------------------------------------------------------------
# Config .env parsing

class TestConfigEnvParsing(unittest.TestCase):
    def _write_env(self, content: str) -> Path:
        fd, path = tempfile.mkstemp(suffix=".env")
        os.close(fd)
        Path(path).write_text(content, encoding="utf-8")
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        return Path(path)

    def test_parses_basic_key_value(self):
        p = self._write_env("SMTP_HOST=smtp.test.com\nSMTP_PORT=587\n")
        parsed = config_mod._parse_env_file(p)
        self.assertEqual(parsed["SMTP_HOST"], "smtp.test.com")
        self.assertEqual(parsed["SMTP_PORT"], "587")

    def test_ignores_comments_and_blanks(self):
        p = self._write_env("# comentario\n\nSMTP_USER=ana@test.com\n")
        parsed = config_mod._parse_env_file(p)
        self.assertEqual(parsed, {"SMTP_USER": "ana@test.com"})

    def test_strips_quotes(self):
        p = self._write_env('SMTP_FROM_NAME="Mi Empresa"\nX=\'valor\'\n')
        parsed = config_mod._parse_env_file(p)
        self.assertEqual(parsed["SMTP_FROM_NAME"], "Mi Empresa")
        self.assertEqual(parsed["X"], "valor")

    def test_supports_export_prefix(self):
        p = self._write_env("export SMTP_PORT=465\n")
        parsed = config_mod._parse_env_file(p)
        self.assertEqual(parsed["SMTP_PORT"], "465")

    def test_get_smtp_config_from_env_file(self):
        p = self._write_env(
            "SMTP_HOST=smtp.example.org\n"
            "SMTP_PORT=2525\n"
            "SMTP_USER=user@example.org\n"
            "SMTP_PASSWORD=secreto123\n"
            "SMTP_USE_SSL=true\n"
        )
        os.environ["LEADHUNTER_ENV"] = str(p)
        try:
            smtp = config_mod.get_smtp_config()
        finally:
            os.environ.pop("LEADHUNTER_ENV", None)
        self.assertEqual(smtp["smtp_host"], "smtp.example.org")
        self.assertEqual(smtp["smtp_port"], 2525)
        self.assertEqual(smtp["smtp_user"], "user@example.org")
        self.assertEqual(smtp["smtp_password"], "secreto123")
        self.assertTrue(smtp["use_ssl"])

    def test_status_never_exposes_password(self):
        p = self._write_env("SMTP_PASSWORD=topsecret\n")
        os.environ["LEADHUNTER_ENV"] = str(p)
        try:
            status = config_mod.smtp_config_status()
        finally:
            os.environ.pop("LEADHUNTER_ENV", None)
        pwd = status["keys"]["SMTP_PASSWORD"]
        self.assertTrue(pwd["configured"])
        self.assertNotIn("topsecret", pwd["display"])
        self.assertEqual(pwd["display"], "configurado")


# ---------------------------------------------------------------------------
# Outreach helpers (offline)

class TestOutreachHelpers(unittest.TestCase):
    def test_unsubscribe_mailto(self):
        url = outreach._unsubscribe_mailto("ventas@empresa.es")
        self.assertEqual(url, "mailto:ventas@empresa.es?subject=BAJA")

    def test_linkedin_message_within_limit(self):
        lead = {"razonSocial": "X" * 400,
                "decisionMakers": [{"name": "Ana Ruiz"}]}
        msg = outreach.generate_linkedin_message(lead)
        self.assertLessEqual(len(msg), 300)

    def test_prepare_email_returns_none_without_email(self):
        self.assertIsNone(outreach.prepare_email({"razonSocial": "Sin Email"}))


# ---------------------------------------------------------------------------
# Levenshtein / normalization (dedup building blocks)

class TestNormalization(unittest.TestCase):
    def test_levenshtein_identical(self):
        self.assertEqual(_common.levenshtein("abc", "abc"), 0)

    def test_levenshtein_one_edit(self):
        self.assertEqual(_common.levenshtein("abc", "abd"), 1)

    def test_normalize_razon_social_drops_legal_form(self):
        self.assertEqual(
            _common.normalize_razon_social("Asesores Pérez, S.L."),
            "asesores perez")


if __name__ == "__main__":
    unittest.main(verbosity=2)
