from src.storage import (
    CrmDatabase,
    count_dialable_leads,
    get_next_dial_lead,
    log_call_outcome,
    upsert_lead,
)
from src.utils.exceptions import CrmDbError
import pytest


def _set_status(db, phone, status):
    with db.connect() as conn:
        conn.execute(
            "UPDATE leads SET status = ? WHERE phone = ?",
            (status, phone),
        )


class TestGetNextDialLead:

    def test_returns_none_when_queue_empty(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        assert get_next_dial_lead(db) is None
        assert count_dialable_leads(db) == 0

    def test_returns_new_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(
            db,
            {
                "company": "Acme Roofing",
                "phone": "5550101001",
                "trade": "roofing",
                "is_hiring": True,
            },
        )

        lead = get_next_dial_lead(db)

        assert lead is not None
        assert lead["company"] == "Acme Roofing"
        assert lead["phone"] == "5550101001"
        assert lead["status"] == "new"
        assert lead["trade"] == "roofing"
        assert lead["is_hiring"] == 1
        assert count_dialable_leads(db) == 1

    def test_prefers_callback_over_new(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "New Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Callback Co", "phone": "5550101002"})
        _set_status(db, "5550101002", "callback")

        lead = get_next_dial_lead(db)

        assert lead["company"] == "Callback Co"
        assert lead["status"] == "callback"
        assert count_dialable_leads(db) == 2

    def test_skips_non_dialable_statuses(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Closed Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Fresh Co", "phone": "5550101002"})
        _set_status(db, "5550101001", "closed")

        lead = get_next_dial_lead(db)

        assert lead["company"] == "Fresh Co"
        assert lead["status"] == "new"
        assert count_dialable_leads(db) == 1

    def test_orders_same_status_by_oldest_updated_at(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "First", "phone": "5550101001"})
        upsert_lead(db, {"company": "Second", "phone": "5550101002"})

        with db.connect() as conn:
            conn.execute(
                "UPDATE leads SET updated_at = ? WHERE phone = ?",
                ("2024-01-01T00:00:00+00:00", "5550101001"),
            )
            conn.execute(
                "UPDATE leads SET updated_at = ? WHERE phone = ?",
                ("2024-06-01T00:00:00+00:00", "5550101002"),
            )

        lead = get_next_dial_lead(db)

        assert lead["company"] == "First"
        assert lead["phone"] == "5550101001"

    def test_empty_statuses_returns_none(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})

        assert get_next_dial_lead(db, statuses=()) is None
        assert count_dialable_leads(db, statuses=()) == 0


class TestLogCallOutcome:

    def test_logs_outcome_and_updates_status(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})
        lead = get_next_dial_lead(db)

        result = log_call_outcome(db, lead["id"], "cb", "try Thursday AM")

        assert result == {
            "lead_id": lead["id"],
            "outcome": "cb",
            "status": "callback",
            "description": "try Thursday AM",
        }

        with db.connect() as conn:
            row = conn.execute(
                "SELECT status FROM leads WHERE id = ?",
                (lead["id"],),
            ).fetchone()
            outcome = conn.execute(
                """
                SELECT outcome, description FROM call_outcomes
                WHERE lead_id = ?
                """,
                (lead["id"],),
            ).fetchone()

        assert row["status"] == "callback"
        assert outcome["outcome"] == "cb"
        assert outcome["description"] == "try Thursday AM"

    @pytest.mark.parametrize(
        "outcome,expected_status",
        [
            ("vm", "new"),
            ("no_answer", "new"),
            ("cb", "callback"),
            ("ni", "not_interested"),
            ("wn", "wrong_number"),
            ("closed", "closed"),
            ("VM", "new"),
        ],
    )
    def test_maps_outcomes_to_statuses(self, tmp_path, outcome, expected_status):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})
        lead = get_next_dial_lead(db)

        result = log_call_outcome(db, lead["id"], outcome)

        assert result["status"] == expected_status

        with db.connect() as conn:
            row = conn.execute(
                "SELECT status FROM leads WHERE id = ?",
                (lead["id"],),
            ).fetchone()
        assert row["status"] == expected_status

    def test_unknown_outcome_raises_value_error(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})
        lead = get_next_dial_lead(db)

        with pytest.raises(ValueError, match="Unknown outcome"):
            log_call_outcome(db, lead["id"], "bogus")

    def test_missing_lead_raises_crm_db_error(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        with pytest.raises(CrmDbError, match="Lead not found"):
            log_call_outcome(db, 999, "vm")

    def test_vm_rotates_lead_in_dial_queue(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "First", "phone": "5550101001"})
        upsert_lead(db, {"company": "Second", "phone": "5550101002"})

        first = get_next_dial_lead(db)
        assert first["company"] == "First"

        log_call_outcome(db, first["id"], "vm", "left voicemail")

        second = get_next_dial_lead(db)
        assert second["company"] == "Second"
        assert count_dialable_leads(db) == 2

    def test_ni_removes_lead_from_dial_queue(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})
        upsert_lead(db, {"company": "Blue Sky HVAC", "phone": "5550101002"})

        lead = get_next_dial_lead(db)
        log_call_outcome(db, lead["id"], "ni", "not interested")

        assert count_dialable_leads(db) == 1
        next_lead = get_next_dial_lead(db)
        assert next_lead["company"] != lead["company"]
