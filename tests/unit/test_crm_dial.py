from src.storage import (
    CrmDatabase,
    count_dialable_leads,
    get_next_dial_lead,
    upsert_lead,
)


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
