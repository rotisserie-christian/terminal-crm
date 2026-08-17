from src.storage import (
    CrmDatabase,
    TOLL_FREE_AREA_CODES,
    area_codes_for_region,
    count_dialable_leads,
    get_next_dial_lead,
    list_dialable_leads,
    log_call_outcome,
    phone_area_code,
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


def _seed_region_leads(db):
    """Insert BC, ON, and toll-free dialable leads for region filter tests."""
    upsert_lead(db, {"company": "BC Co", "phone": "+1 604-555-0101"})
    upsert_lead(db, {"company": "ON Co", "phone": "+1 416-555-0102"})
    upsert_lead(db, {"company": "Toll Free Co", "phone": "+1 888-555-0103"})


class TestPhoneAreaCode:

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("6045550101", "604"),
            ("16045550101", "604"),
            ("+1 604-555-0101", "604"),
            ("4165550102", "416"),
            ("18885550103", "888"),
            (None, None),
            ("", None),
            ("555", None),
        ],
    )
    def test_extracts_npa(self, phone, expected):
        assert phone_area_code(phone) == expected


class TestAreaCodesForRegion:

    def test_none_and_blank_mean_no_filter(self):
        assert area_codes_for_region(None) is None
        assert area_codes_for_region("") is None
        assert area_codes_for_region("   ") is None

    def test_resolves_bc_and_on(self):
        bc = area_codes_for_region("bc")
        on = area_codes_for_region("ON")

        assert bc is not None and "604" in bc and "778" in bc
        assert on is not None and "416" in on and "647" in on
        assert bc == tuple(sorted(bc))
        assert on == tuple(sorted(on))

    def test_excludes_toll_free_from_regions(self):
        for region in ("bc", "on"):
            codes = area_codes_for_region(region)
            assert codes is not None
            assert TOLL_FREE_AREA_CODES.isdisjoint(codes)

    def test_unknown_region_raises(self):
        with pytest.raises(ValueError, match="Unknown dial region"):
            area_codes_for_region("ab")


class TestDialRegionFilter:

    def test_full_list_includes_all_numbers(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        assert count_dialable_leads(db) == 3
        assert count_dialable_leads(db, region=None) == 3

    def test_bc_filter_returns_only_bc(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        assert count_dialable_leads(db, region="bc") == 1
        lead = get_next_dial_lead(db, region="bc")
        assert lead is not None
        assert lead["company"] == "BC Co"
        assert phone_area_code(lead["phone"]) == "604"

    def test_on_filter_returns_only_on(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        assert count_dialable_leads(db, region="on") == 1
        lead = get_next_dial_lead(db, region="on")
        assert lead is not None
        assert lead["company"] == "ON Co"
        assert phone_area_code(lead["phone"]) == "416"

    def test_location_filter_excludes_toll_free(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Toll Free Co", "phone": "18885550103"})

        assert count_dialable_leads(db) == 1
        assert count_dialable_leads(db, region="bc") == 0
        assert count_dialable_leads(db, region="on") == 0
        assert get_next_dial_lead(db, region="bc") is None
        assert get_next_dial_lead(db, region="on") is None

    def test_region_filter_respects_callback_priority(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "BC New", "phone": "6045550101"})
        upsert_lead(db, {"company": "BC Callback", "phone": "7785550102"})
        upsert_lead(db, {"company": "ON Callback", "phone": "4165550103"})
        _set_status(db, "7785550102", "callback")
        _set_status(db, "4165550103", "callback")

        lead = get_next_dial_lead(db, region="bc")
        assert lead["company"] == "BC Callback"
        assert count_dialable_leads(db, region="bc") == 2

    def test_unknown_region_raises_on_dial_helpers(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "BC Co", "phone": "6045550101"})

        with pytest.raises(ValueError, match="Unknown dial region"):
            get_next_dial_lead(db, region="qc")
        with pytest.raises(ValueError, match="Unknown dial region"):
            list_dialable_leads(db, region="qc")
        with pytest.raises(ValueError, match="Unknown dial region"):
            count_dialable_leads(db, region="qc")


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


class TestListDialableLeads:

    def test_returns_empty_when_queue_empty(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))

        assert list_dialable_leads(db) == []

    def test_first_item_matches_get_next_dial_lead(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "New Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Callback Co", "phone": "5550101002"})
        _set_status(db, "5550101002", "callback")

        leads = list_dialable_leads(db)
        nxt = get_next_dial_lead(db)

        assert len(leads) == 2
        assert nxt is not None
        assert leads[0] == nxt
        assert leads[0]["company"] == "Callback Co"

    def test_prefers_callback_over_new(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "New Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Callback Co", "phone": "5550101002"})
        _set_status(db, "5550101002", "callback")

        companies = [lead["company"] for lead in list_dialable_leads(db)]

        assert companies == ["Callback Co", "New Co"]

    def test_skips_non_dialable_statuses(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Closed Co", "phone": "5550101001"})
        upsert_lead(db, {"company": "Fresh Co", "phone": "5550101002"})
        _set_status(db, "5550101001", "closed")

        leads = list_dialable_leads(db)

        assert [lead["company"] for lead in leads] == ["Fresh Co"]
        assert leads[0]["status"] == "new"

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

        companies = [lead["company"] for lead in list_dialable_leads(db)]

        assert companies == ["First", "Second"]

    def test_empty_statuses_returns_empty(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Acme Roofing", "phone": "5550101001"})

        assert list_dialable_leads(db, statuses=()) == []

    def test_full_list_includes_all_numbers(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        companies = [lead["company"] for lead in list_dialable_leads(db)]

        assert companies == ["BC Co", "ON Co", "Toll Free Co"]

    def test_region_filter_returns_only_matching_location(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        _seed_region_leads(db)

        bc = [lead["company"] for lead in list_dialable_leads(db, region="bc")]
        on = [lead["company"] for lead in list_dialable_leads(db, region="on")]

        assert bc == ["BC Co"]
        assert on == ["ON Co"]

    def test_location_filter_excludes_toll_free(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "Toll Free Co", "phone": "18885550103"})

        assert list_dialable_leads(db, region="bc") == []
        assert list_dialable_leads(db, region="on") == []
        assert [lead["company"] for lead in list_dialable_leads(db)] == [
            "Toll Free Co"
        ]

    def test_region_filter_respects_callback_priority(self, tmp_path):
        db = CrmDatabase(str(tmp_path / "crm.db"))
        upsert_lead(db, {"company": "BC New", "phone": "6045550101"})
        upsert_lead(db, {"company": "BC Callback", "phone": "7785550102"})
        upsert_lead(db, {"company": "ON Callback", "phone": "4165550103"})
        _set_status(db, "7785550102", "callback")
        _set_status(db, "4165550103", "callback")

        companies = [
            lead["company"] for lead in list_dialable_leads(db, region="bc")
        ]

        assert companies == ["BC Callback", "BC New"]


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
