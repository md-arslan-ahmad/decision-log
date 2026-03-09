"""
Shared test utilities.

Each test that needs a DB gets a fresh in-memory SQLite database via AppTestCase.
Tests are completely isolated — no shared state between test methods.
"""
import os
import sys
import tempfile
import unittest

# Add backend directory to path so imports work without install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


class AppTestCase(unittest.TestCase):
    """
    Base class for tests that need the Flask app + a fresh database.
    Each test method gets a new temp file database.
    """

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.app = create_app({
            "TESTING": True,
            "DB_PATH": self.db_path,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # ── Convenience helpers ────────────────────────────────────────────────────

    VALID_PAYLOAD = {
        "title": "Use Flask for the API",
        "context": "We need a simple Python web framework for our REST API.",
        "decision": "We will use Flask because it is lightweight and well-documented.",
    }

    def create_decision(self, payload=None) -> dict:
        """Create a decision and return the response body dict."""
        resp = self.client.post(
            "/api/decisions/",
            json=payload or self.VALID_PAYLOAD,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()["data"]
