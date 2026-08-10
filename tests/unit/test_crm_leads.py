import pytest

from src.storage import CrmDatabase, merge_leads, normalize_phone, upsert_lead
from src.storage.crm_leads import to_bool_int


class TestNormalizePhone:

    def test_strips_non_digits(self):
        assert normalize_phone("(555) 010-1001") == "5550101001"

    def test_keeps_digit_string(self):
        assert normalize_phone("5550101001") == "5550101001"

    def test_returns_none_for_missing_or_invalid(self):
        assert normalize_phone(None) is None
        assert normalize_phone("") is None
        assert normalize_phone("abc") is None
        assert normalize_phone("---") is None


class TestToBoolInt:

    @pytest.mark.parametrize(
        "value,expected",
        [
            (True, 1),
            (False, 0),
            (1, 1),
            (0, 0),
            ("true", 1),
            ("YES", 1),
            ("y", 1),
            ("false", 0),
            ("NO", 0),
            ("n", 0),
            ("", 0),
            (None, 0),
            ("maybe", 0),
        ],
    )
    def test_coerces_common_values(self, value, expected):
        assert to_bool_int(value) == expected


class TestUpsertLead:

    def test_inserts_new_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        result = upsert_lead(
            db,
            {
                "company": "Acme Roofing",
                "website": "https://acmeroof.example",
                "trade": "roofing",
                "signals": "new trucks",
                "hiring": "1 estimator",
                "phone": "555-010-1001",
                "is_hiring": True,
                "has_ads": "yes",
            },
        )

        assert result == "added"

        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE phone = ?",
                ("5550101001",),
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]

        assert count == 1
        assert row["company"] == "Acme Roofing"
        assert row["phone"] == "5550101001"
        assert row["is_hiring"] == 1
        assert row["has_ads"] == 1
        assert row["status"] == "new"

    def test_updates_existing_lead_by_normalized_phone(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        upsert_lead(
            db,
            {
                "company": "Acme Roofing",
                "phone": "5550101001",
                "trade": "roofing",
                "is_hiring": True,
                "has_ads": False,
            },
        )

        with db.connect() as conn:
            conn.execute(
                "UPDATE leads SET status = ? WHERE phone = ?",
                ("callback", "5550101001"),
            )
            original = conn.execute(
                "SELECT created_at, status FROM leads WHERE phone = ?",
                ("5550101001",),
            ).fetchone()

        result = upsert_lead(
            db,
            {
                "company": "Acme Roofing LLC",
                "phone": "(555) 010-1001",
                "trade": "commercial roofing",
                "signals": "google ads",
                "hiring": "2 estimators",
                "is_hiring": False,
                "has_ads": True,
            },
        )

        assert result == "updated"

        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE phone = ?",
                ("5550101001",),
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]

        assert count == 1
        assert row["company"] == "Acme Roofing LLC"
        assert row["trade"] == "commercial roofing"
        assert row["signals"] == "google ads"
        assert row["hiring"] == "2 estimators"
        assert row["is_hiring"] == 0
        assert row["has_ads"] == 1
        assert row["status"] == "callback"
        assert row["created_at"] == original["created_at"]
        assert row["updated_at"] >= original["created_at"]

    def test_skips_missing_or_invalid_phone(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        assert upsert_lead(db, {"company": "No Phone", "phone": ""}) == "skipped"
        assert upsert_lead(db, {"company": "No Phone", "phone": None}) == "skipped"
        assert upsert_lead(db, {"company": "No Phone", "phone": "n/a"}) == "skipped"

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]

        assert count == 0


class TestMergeLeads:

    def test_merge_summary_for_add_update_and_skip(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        upsert_lead(
            db,
            {"company": "Acme Roofing", "phone": "5550101001", "trade": "roofing"},
        )

        summary = merge_leads(
            db,
            [
                {
                    "company": "Acme Roofing LLC",
                    "phone": "555-010-1001",
                    "trade": "commercial roofing",
                },
                {"company": "Blue Sky HVAC", "phone": "5550101002"},
                {"company": "Missing Phone", "phone": ""},
                "not-a-lead",
            ],
        )

        assert summary == {"added": 1, "updated": 1, "skipped": 2}

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT company, phone, trade FROM leads ORDER BY phone"
            ).fetchall()

        assert len(rows) == 2
        assert rows[0]["phone"] == "5550101001"
        assert rows[0]["company"] == "Acme Roofing LLC"
        assert rows[0]["trade"] == "commercial roofing"
        assert rows[1]["phone"] == "5550101002"
        assert rows[1]["company"] == "Blue Sky HVAC"

    def test_different_phones_insert_separately(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        summary = merge_leads(
            db,
            [
                {"company": "Acme Roofing", "phone": "5550101001"},
                {"company": "Blue Sky HVAC", "phone": "5550101002"},
                {"company": "Pine Plumbing", "phone": "5550101003"},
            ],
        )

        assert summary == {"added": 3, "updated": 0, "skipped": 0}

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]

        assert count == 3
