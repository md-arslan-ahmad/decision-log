"""
Integration tests for /api/decisions HTTP endpoints.
Tests the full stack: routes -> service -> repository -> in-memory DB.
"""
import unittest

from tests.helpers import AppTestCase


class TestHealthCheck(AppTestCase):

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")


class TestCreateDecision(AppTestCase):

    def test_create_returns_201(self):
        resp = self.client.post("/api/decisions/", json=self.VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 201)

    def test_create_returns_proposed_status(self):
        resp = self.client.post("/api/decisions/", json=self.VALID_PAYLOAD)
        self.assertEqual(resp.get_json()["data"]["status"], "proposed")

    def test_create_returns_id(self):
        resp = self.client.post("/api/decisions/", json=self.VALID_PAYLOAD)
        self.assertIn("id", resp.get_json()["data"])

    def test_create_without_json_content_type_returns_415(self):
        import json
        resp = self.client.post(
            "/api/decisions/",
            data=json.dumps(self.VALID_PAYLOAD),
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, 415)

    def test_create_with_short_title_returns_422(self):
        resp = self.client.post(
            "/api/decisions/",
            json={**self.VALID_PAYLOAD, "title": "Hi"},
        )
        self.assertEqual(resp.status_code, 422)
        body = resp.get_json()
        self.assertEqual(body["code"], "VALIDATION_ERROR")
        self.assertIn("details", body)

    def test_create_missing_required_field_returns_422(self):
        resp = self.client.post(
            "/api/decisions/",
            json={"title": "Only a title here"},
        )
        self.assertEqual(resp.status_code, 422)

    def test_response_envelope_has_data_key(self):
        resp = self.client.post("/api/decisions/", json=self.VALID_PAYLOAD)
        self.assertIn("data", resp.get_json())

    def test_create_with_malformed_json_returns_400(self):
        resp = self.client.post(
            "/api/decisions/",
            data="not json at all",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestListDecisions(AppTestCase):

    def test_empty_list_returns_200(self):
        resp = self.client.get("/api/decisions/")
        self.assertEqual(resp.status_code, 200)

    def test_empty_list_has_data_and_meta(self):
        resp = self.client.get("/api/decisions/")
        body = resp.get_json()
        self.assertEqual(body["data"], [])
        self.assertEqual(body["meta"]["count"], 0)

    def test_after_create_count_is_1(self):
        self.create_decision()
        resp = self.client.get("/api/decisions/")
        self.assertEqual(resp.get_json()["meta"]["count"], 1)

    def test_after_two_creates_count_is_2(self):
        self.create_decision()
        self.create_decision()
        resp = self.client.get("/api/decisions/")
        self.assertEqual(resp.get_json()["meta"]["count"], 2)


class TestGetDecision(AppTestCase):

    def test_get_existing_returns_200(self):
        decision = self.create_decision()
        resp = self.client.get(f"/api/decisions/{decision['id']}")
        self.assertEqual(resp.status_code, 200)

    def test_get_existing_returns_correct_data(self):
        decision = self.create_decision()
        resp = self.client.get(f"/api/decisions/{decision['id']}")
        self.assertEqual(resp.get_json()["data"]["id"], decision["id"])

    def test_get_nonexistent_returns_404(self):
        resp = self.client.get("/api/decisions/99999")
        self.assertEqual(resp.status_code, 404)

    def test_not_found_error_has_code(self):
        resp = self.client.get("/api/decisions/99999")
        self.assertEqual(resp.get_json()["code"], "NOT_FOUND")


class TestTransitionDecision(AppTestCase):

    def test_valid_transition_proposed_to_accepted(self):
        decision = self.create_decision()
        resp = self.client.post(
            f"/api/decisions/{decision['id']}/transition",
            json={"status": "accepted"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["status"], "accepted")

    def test_valid_transition_proposed_to_rejected(self):
        decision = self.create_decision()
        resp = self.client.post(
            f"/api/decisions/{decision['id']}/transition",
            json={"status": "rejected"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_invalid_transition_returns_422(self):
        decision = self.create_decision()
        resp = self.client.post(
            f"/api/decisions/{decision['id']}/transition",
            json={"status": "superseded"},  # proposed -> superseded is forbidden
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.get_json()["code"], "INVALID_TRANSITION")

    def test_unknown_status_returns_422(self):
        decision = self.create_decision()
        resp = self.client.post(
            f"/api/decisions/{decision['id']}/transition",
            json={"status": "banana"},
        )
        self.assertEqual(resp.status_code, 422)

    def test_missing_status_field_returns_400(self):
        decision = self.create_decision()
        resp = self.client.post(
            f"/api/decisions/{decision['id']}/transition",
            json={},
        )
        self.assertEqual(resp.status_code, 400)

    def test_transition_nonexistent_returns_404(self):
        resp = self.client.post(
            "/api/decisions/99999/transition",
            json={"status": "accepted"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_full_lifecycle_proposed_accepted_superseded(self):
        """Walk a decision through its full happy-path lifecycle."""
        decision = self.create_decision()
        did = decision["id"]

        resp = self.client.post(f"/api/decisions/{did}/transition", json={"status": "accepted"})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(f"/api/decisions/{did}/transition", json={"status": "superseded"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["status"], "superseded")


class TestUpdateDecision(AppTestCase):

    def test_partial_update_title(self):
        decision = self.create_decision()
        resp = self.client.patch(
            f"/api/decisions/{decision['id']}",
            json={"title": "Updated framework decision for API"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["title"], "Updated framework decision for API")

    def test_partial_update_does_not_change_other_fields(self):
        decision = self.create_decision()
        resp = self.client.patch(
            f"/api/decisions/{decision['id']}",
            json={"title": "New valid title for the decision"},
        )
        self.assertEqual(resp.get_json()["data"]["context"], decision["context"])

    def test_update_nonexistent_returns_404(self):
        resp = self.client.patch(
            "/api/decisions/99999",
            json={"title": "Ghost update right here for test"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_short_title_returns_422(self):
        decision = self.create_decision()
        resp = self.client.patch(
            f"/api/decisions/{decision['id']}",
            json={"title": "Hi"},
        )
        self.assertEqual(resp.status_code, 422)


class TestDeleteDecision(AppTestCase):

    def test_delete_returns_204(self):
        decision = self.create_decision()
        resp = self.client.delete(f"/api/decisions/{decision['id']}")
        self.assertEqual(resp.status_code, 204)

    def test_deleted_decision_returns_404_on_get(self):
        decision = self.create_decision()
        self.client.delete(f"/api/decisions/{decision['id']}")
        resp = self.client.get(f"/api/decisions/{decision['id']}")
        self.assertEqual(resp.status_code, 404)

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete("/api/decisions/99999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
