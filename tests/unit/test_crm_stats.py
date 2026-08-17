import pytest

from src.storage import (
    CrmDatabase,
    LEAD_STATUSES,
    lead_status_counts,
    log_call_outcome,
    outcome_counts,
    upsert_lead,
)


def _set_status(db, phone, status):
    with db.connect() as conn:
        conn.execute(
            "UPDATE leads SET status = ? WHERE phone = ?",
            (status, phone),
        )


def _seed_region_leads(db):
    upsert_lead(db, {"company": "BC Co", "phone": "+1 604-555-0101"})
    upsert_lead(db, {"company": "ON Co", "phone": "+1 416-555-0102"})
    upsert_lead(db, {"company": "Toll Free Co", "phone": "+1 888-555-0103"})


class TestLeadStatusCounts:

    def test_empty_database_is_all_zeros(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        result = lead_status_counts(db)

        assert result["total"] == 0
        assert result["queue"] == 0
        assert result["by_status"] == {status: 0 for status in LEAD_STATUSES}

    def test_full_list_includes_parked_and_queue(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "New Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Callback Co", "phone": "5550101002"})
        upsert_lead(db, {"company": "Closed Co", "phone": "5550101003"})
        upsert_lead(db, {"company": "Dnc Co", "phone": "5550101004"})
        _set_status(db, "5550101002", "callback")
        _set_status(db, "5550101003", "closed")
        _set_status(db, "5550101004", "do_not_call")

        result = lead_status_counts(db)

        assert result["total"] == 4
        assert result["queue"] == 2
        assert result["by_status"]["new"] == 1
        assert result["by_status"]["callback"] == 1
        assert result["by_status"]["closed"] == 1
        assert result["by_status"]["do_not_call"] == 1
        assert result["by_status"]["not_interested"] == 0

    def test_full_list_includes_all_numbers(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        result = lead_status_counts(db)

        assert result["total"] == 3
        assert result["queue"] == 3

    def test_bc_filter_includes_closed_leads(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)
        upsert_lead(db, {"company": "BC Closed", "phone": "7785550104"})
        _set_status(db, "7785550104", "closed")

        result = lead_status_counts(db, region="bc")

        assert result["total"] == 2
        assert result["queue"] == 1
        assert result["by_status"]["new"] == 1
        assert result["by_status"]["closed"] == 1

    def test_on_filter_returns_only_on(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        result = lead_status_counts(db, region="on")

        assert result["total"] == 1
        assert result["queue"] == 1

    def test_location_filter_excludes_toll_free(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Toll Free Co", "phone": "18885550103"})
        _set_status(db, "18885550103", "closed")

        assert lead_status_counts(db)["total"] == 1
        assert lead_status_counts(db, region="bc")["total"] == 0
        assert lead_status_counts(db, region="on")["total"] == 0

    def test_unknown_region_raises(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "BC Co", "phone": "6045550101"})

        with pytest.raises(ValueError, match="Unknown dial region"):
            lead_status_counts(db, region="qc")


def _lead_id(db, phone):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id FROM leads WHERE phone = ?",
            (phone,),
        ).fetchone()
    return row["id"]


class TestOutcomeCounts:

    def test_empty_database_is_all_zeros(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        result = outcome_counts(db)

        assert result["total"] == 0
        assert result["by_outcome"]["vm"] == 0
        assert result["by_outcome"]["ni"] == 0
        assert result["by_outcome"]["dnc"] == 0

    def test_counts_each_logged_outcome(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme", "phone": "5550101001"})
        upsert_lead(db, {"company": "Blue", "phone": "5550101002"})
        log_call_outcome(db, _lead_id(db, "5550101001"), "vm")
        log_call_outcome(db, _lead_id(db, "5550101002"), "ni")
        log_call_outcome(db, _lead_id(db, "5550101002"), "dnc")

        result = outcome_counts(db)

        assert result["total"] == 3
        assert result["by_outcome"]["vm"] == 1
        assert result["by_outcome"]["ni"] == 1
        assert result["by_outcome"]["dnc"] == 1
        assert result["by_outcome"]["cb"] == 0

    def test_counts_multiple_outcomes_on_same_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme", "phone": "5550101001"})
        lead_id = _lead_id(db, "5550101001")
        log_call_outcome(db, lead_id, "vm")
        log_call_outcome(db, lead_id, "vm")
        log_call_outcome(db, lead_id, "cb")

        result = outcome_counts(db)

        assert result["total"] == 3
        assert result["by_outcome"]["vm"] == 2
        assert result["by_outcome"]["cb"] == 1

    def test_region_filter_uses_lead_phone(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)
        log_call_outcome(db, _lead_id(db, "16045550101"), "vm")
        log_call_outcome(db, _lead_id(db, "14165550102"), "ni")
        log_call_outcome(db, _lead_id(db, "18885550103"), "closed")

        full = outcome_counts(db)
        bc = outcome_counts(db, region="bc")
        on = outcome_counts(db, region="on")

        assert full["total"] == 3
        assert bc["total"] == 1
        assert bc["by_outcome"]["vm"] == 1
        assert on["total"] == 1
        assert on["by_outcome"]["ni"] == 1

    def test_location_filter_excludes_toll_free(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Toll Free Co", "phone": "18885550103"})
        log_call_outcome(db, _lead_id(db, "18885550103"), "vm")

        assert outcome_counts(db)["total"] == 1
        assert outcome_counts(db, region="bc")["total"] == 0
        assert outcome_counts(db, region="on")["total"] == 0

    def test_unknown_region_raises(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "BC Co", "phone": "6045550101"})

        with pytest.raises(ValueError, match="Unknown dial region"):
            outcome_counts(db, region="qc")
