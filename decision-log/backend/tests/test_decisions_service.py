"""
Tests for DecisionsService — business rules and validation.
Uses a real in-memory DB via AppTestCase.
"""
import unittest

from tests.helpers import AppTestCase
from models.decision import DecisionStatus, InvalidTransitionError
from repositories.decisions_repository import DecisionsRepository
from services.decisions_service import DecisionsService, NotFoundError, ValidationError


class ServiceTestCase(AppTestCase):
    def setUp(self):
        super().setUp()
        # Build service inside app context
        self._service_ctx = self.app.app_context()
        self._service_ctx.push()
        self.service = DecisionsService(repo=DecisionsRepository())

    def tearDown(self):
        self._service_ctx.pop()
        super().tearDown()

    VALID = {
        "title": "Use SQLite for development",
        "context": "We need a lightweight DB for local development purposes.",
        "decision": "We will use SQLite during development and swap later.",
    }


class TestCreateDecision(ServiceTestCase):

    def test_creates_with_proposed_status(self):
        d = self.service.create_decision(self.VALID)
        self.assertEqual(d.status, DecisionStatus.PROPOSED)

    def test_title_too_short_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self.service.create_decision({**self.VALID, "title": "Hi"})
        fields = [e["field"] for e in ctx.exception.errors]
        self.assertIn("title", fields)

    def test_missing_context_raises_validation_error(self):
        data = {"title": "Valid title here", "decision": "Valid decision text here."}
        with self.assertRaises(ValidationError):
            self.service.create_decision(data)

    def test_strips_whitespace_from_title(self):
        d = self.service.create_decision({**self.VALID, "title": "  Use Postgres  "})
        self.assertEqual(d.title, "Use Postgres")

    def test_consequences_is_optional(self):
        d = self.service.create_decision(self.VALID)
        self.assertIsNone(d.consequences)

    def test_consequences_is_saved_when_provided(self):
        d = self.service.create_decision({**self.VALID, "consequences": "Team needs training"})
        self.assertEqual(d.consequences, "Team needs training")


class TestGetDecision(ServiceTestCase):

    def test_get_existing_returns_decision(self):
        created = self.service.create_decision(self.VALID)
        found = self.service.get_decision(created.id)
        self.assertEqual(found.id, created.id)

    def test_get_nonexistent_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.service.get_decision(99999)


class TestTransitionDecision(ServiceTestCase):

    def test_proposed_to_accepted(self):
        d = self.service.create_decision(self.VALID)
        updated = self.service.transition_decision(d.id, "accepted")
        self.assertEqual(updated.status, DecisionStatus.ACCEPTED)

    def test_invalid_transition_raises_invalid_transition_error(self):
        d = self.service.create_decision(self.VALID)
        with self.assertRaises(InvalidTransitionError):
            self.service.transition_decision(d.id, "superseded")

    def test_unknown_status_raises_validation_error(self):
        d = self.service.create_decision(self.VALID)
        with self.assertRaises(ValidationError):
            self.service.transition_decision(d.id, "flying")

    def test_transition_nonexistent_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.service.transition_decision(99999, "accepted")


class TestUpdateDecision(ServiceTestCase):

    def test_partial_update_title(self):
        d = self.service.create_decision(self.VALID)
        updated = self.service.update_decision(d.id, {"title": "Updated development DB choice"})
        self.assertEqual(updated.title, "Updated development DB choice")

    def test_other_fields_unchanged_after_partial_update(self):
        d = self.service.create_decision(self.VALID)
        updated = self.service.update_decision(d.id, {"title": "New valid title here for it"})
        self.assertEqual(updated.context, d.context)

    def test_update_nonexistent_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.service.update_decision(99999, {"title": "Ghost update right here"})

    def test_short_title_raises_validation_error(self):
        d = self.service.create_decision(self.VALID)
        with self.assertRaises(ValidationError):
            self.service.update_decision(d.id, {"title": "Hi"})


class TestDeleteDecision(ServiceTestCase):

    def test_delete_removes_record(self):
        d = self.service.create_decision(self.VALID)
        self.service.delete_decision(d.id)
        with self.assertRaises(NotFoundError):
            self.service.get_decision(d.id)

    def test_delete_nonexistent_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.service.delete_decision(99999)


if __name__ == "__main__":
    unittest.main()
