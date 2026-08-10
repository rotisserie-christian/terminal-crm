from datetime import datetime, timezone

import pytest
import sqlite3

from src.storage import CrmDatabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestCrmDatabase:

    def test_creates_db_file_and_parent_dir(self, tmp_path):
        db_path = tmp_path / "nested" / "crm.db"
        db = CrmDatabase(str(db_path))

        assert db_path.exists()
        assert db_path.parent.is_dir()

    def test_creates_leads_and_call_outcomes_tables(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        assert db.table_names() == ["call_outcomes", "leads"]

    def test_initialize_schema_is_idempotent(self, tmp_path):
        db_path = str(tmp_path / "crm.db")
        CrmDatabase(db_path)
        db = CrmDatabase(db_path)

        assert db.table_names() == ["call_outcomes", "leads"]

    def test_can_insert_and_read_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        now = _now()

        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO leads (
                    company, website, trade, signals, hiring, phone,
                    is_hiring, has_ads, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Acme Roofing",
                    "https://acmeroof.example",
                    "roofing",
                    "new trucks, google ads",
                    "1 estimator",
                    "5550101001",
                    1,
                    1,
                    now,
                    now,
                ),
            )

        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE phone = ?",
                ("5550101001",),
            ).fetchone()

        assert row is not None
        assert row["company"] == "Acme Roofing"
        assert row["website"] == "https://acmeroof.example"
        assert row["trade"] == "roofing"
        assert row["signals"] == "new trucks, google ads"
        assert row["hiring"] == "1 estimator"
        assert row["phone"] == "5550101001"
        assert row["status"] == "new"

    def test_boolean_fields_round_trip_as_integers(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        now = _now()

        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO leads (
                    company, phone, is_hiring, has_ads, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Blue Sky HVAC", "5550101002", 1, 0, now, now),
            )

        with db.connect() as conn:
            row = conn.execute(
                "SELECT is_hiring, has_ads FROM leads WHERE phone = ?",
                ("5550101002",),
            ).fetchone()

        assert row["is_hiring"] == 1
        assert row["has_ads"] == 0
        assert isinstance(row["is_hiring"], int)
        assert isinstance(row["has_ads"], int)

    def test_unique_phone_index_rejects_duplicates(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        now = _now()

        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO leads (company, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("Acme Roofing", "5550101001", now, now),
            )

        with pytest.raises(sqlite3.IntegrityError):
            with db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO leads (company, phone, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("Other Co", "5550101001", now, now),
                )

    def test_can_insert_call_outcome_for_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        now = _now()

        with db.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO leads (company, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("Pine Plumbing", "5550101003", now, now),
            )
            lead_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO call_outcomes (lead_id, outcome, description, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (lead_id, "vm", "left voicemail", now),
            )

        with db.connect() as conn:
            row = conn.execute(
                """
                SELECT outcome, description FROM call_outcomes
                WHERE lead_id = ?
                """,
                (lead_id,),
            ).fetchone()

        assert row["outcome"] == "vm"
        assert row["description"] == "left voicemail"

