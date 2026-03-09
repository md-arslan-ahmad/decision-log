"""
Unit tests for Decision model — pure Python, no DB required.

Tests focus on the state machine logic: valid transitions, invalid transitions,
and the invariant that status changes always go through transition().
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.decision import Decision, DecisionStatus, InvalidTransitionError


def _make_decision(**kwargs) -> Decision:
    defaults = dict(
        title="Use PostgreSQL",
        context="We need a relational database for our project.",
        decision_text="We will use PostgreSQL in all environments.",
    )
    defaults.update(kwargs)
    return Decision(**defaults)


class TestDecisionTransition(unittest.TestCase):

    def test_proposed_to_accepted_is_allowed(self):
        d = _make_decision()
        d.transition(DecisionStatus.ACCEPTED)
        self.assertEqual(d.status, DecisionStatus.ACCEPTED)

    def test_proposed_to_rejected_is_allowed(self):
        d = _make_decision()
        d.transition(DecisionStatus.REJECTED)
        self.assertEqual(d.status, DecisionStatus.REJECTED)

    def test_accepted_to_superseded_is_allowed(self):
        d = _make_decision(status=DecisionStatus.ACCEPTED)
        d.transition(DecisionStatus.SUPERSEDED)
        self.assertEqual(d.status, DecisionStatus.SUPERSEDED)

    def test_proposed_to_superseded_is_forbidden(self):
        d = _make_decision()
        with self.assertRaises(InvalidTransitionError):
            d.transition(DecisionStatus.SUPERSEDED)

    def test_rejected_to_accepted_is_forbidden(self):
        d = _make_decision(status=DecisionStatus.REJECTED)
        with self.assertRaises(InvalidTransitionError):
            d.transition(DecisionStatus.ACCEPTED)

    def test_superseded_to_anything_is_forbidden(self):
        d = _make_decision(status=DecisionStatus.SUPERSEDED)
        for target in [DecisionStatus.PROPOSED, DecisionStatus.ACCEPTED, DecisionStatus.REJECTED]:
            with self.subTest(target=target):
                d2 = _make_decision(status=DecisionStatus.SUPERSEDED)
                with self.assertRaises(InvalidTransitionError):
                    d2.transition(target)

    def test_rejected_is_terminal(self):
        d = _make_decision(status=DecisionStatus.REJECTED)
        with self.assertRaises(InvalidTransitionError):
            d.transition(DecisionStatus.REJECTED)  # even same status is forbidden

    def test_transition_updates_status(self):
        d = _make_decision()
        original_updated = d.updated_at
        d.transition(DecisionStatus.ACCEPTED)
        self.assertGreaterEqual(d.updated_at, original_updated)

    def test_error_message_includes_target_status(self):
        d = _make_decision()
        try:
            d.transition(DecisionStatus.SUPERSEDED)
        except InvalidTransitionError as exc:
            self.assertIn("superseded", str(exc))
        else:
            self.fail("Expected InvalidTransitionError")


class TestDecisionToDict(unittest.TestCase):

    def test_to_dict_has_all_expected_keys(self):
        d = _make_decision()
        result = d.to_dict()
        expected = {"id", "title", "context", "decision", "consequences", "status", "created_at", "updated_at"}
        self.assertEqual(set(result.keys()), expected)

    def test_to_dict_uses_decision_key_not_decision_text(self):
        """The ORM column name 'decision_text' must not leak into the API."""
        d = _make_decision()
        result = d.to_dict()
        self.assertIn("decision", result)
        self.assertNotIn("decision_text", result)

    def test_to_dict_status_is_string(self):
        d = _make_decision()
        result = d.to_dict()
        self.assertIsInstance(result["status"], str)
        self.assertEqual(result["status"], "proposed")


if __name__ == "__main__":
    unittest.main()
