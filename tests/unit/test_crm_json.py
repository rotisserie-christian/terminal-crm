import json

import pytest

from src.storage import list_lead_files, load_leads_directory, load_leads_file
from src.utils.exceptions import LeadLoadError


class TestLoadLeadsFile:

    def test_loads_top_level_array(self, tmp_path):
        path = tmp_path / "leads.json"
        path.write_text(
            json.dumps(
                [
                    {"company": "Acme Roofing", "phone": "5550101001"},
                    {"company": "Blue Sky HVAC", "phone": "5550101002"},
                ]
            ),
            encoding="utf-8",
        )

        leads = load_leads_file(path)

        assert len(leads) == 2
        assert leads[0]["company"] == "Acme Roofing"
        assert leads[1]["phone"] == "5550101002"

    def test_loads_wrapped_leads_object(self, tmp_path):
        path = tmp_path / "leads.json"
        path.write_text(
            json.dumps(
                {
                    "leads": [
                        {"company": "Pine Plumbing", "phone": "5550101003"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        leads = load_leads_file(path)

        assert len(leads) == 1
        assert leads[0]["company"] == "Pine Plumbing"

    def test_loads_repo_sample_json(self):
        leads = load_leads_file("leads/sample.json")

        assert len(leads) == 3
        assert leads[0]["company"] == "Acme Roofing"
        assert leads[0]["is_hiring"] is True
        assert leads[2]["has_ads"] is False

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_leads_file(tmp_path / "missing.json")

    def test_invalid_json_raises_lead_load_error(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(LeadLoadError, match="corrupted"):
            load_leads_file(path)

    def test_invalid_top_level_shape_raises_lead_load_error(self, tmp_path):
        path = tmp_path / "bad_shape.json"
        path.write_text(json.dumps({"companies": []}), encoding="utf-8")

        with pytest.raises(LeadLoadError, match="expected a list"):
            load_leads_file(path)

    def test_non_object_entry_raises_lead_load_error(self, tmp_path):
        path = tmp_path / "bad_entry.json"
        path.write_text(json.dumps([{"company": "Ok"}, "nope"]), encoding="utf-8")

        with pytest.raises(LeadLoadError, match="index 1"):
            load_leads_file(path)


class TestListLeadFiles:

    def test_returns_sorted_json_files(self, tmp_path):
        (tmp_path / "b.json").write_text("[]", encoding="utf-8")
        (tmp_path / "a.json").write_text("[]", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

        files = list_lead_files(tmp_path)

        assert [path.name for path in files] == ["a.json", "b.json"]

    def test_missing_directory_returns_empty_list(self, tmp_path):
        assert list_lead_files(tmp_path / "missing") == []


class TestLoadLeadsDirectory:

    def test_concatenates_leads_from_all_json_files(self, tmp_path):
        (tmp_path / "one.json").write_text(
            json.dumps([{"company": "Acme Roofing", "phone": "5550101001"}]),
            encoding="utf-8",
        )
        (tmp_path / "two.json").write_text(
            json.dumps({"leads": [{"company": "Blue Sky HVAC", "phone": "5550101002"}]}),
            encoding="utf-8",
        )

        leads = load_leads_directory(tmp_path)

        assert len(leads) == 2
        companies = {lead["company"] for lead in leads}
        assert companies == {"Acme Roofing", "Blue Sky HVAC"}

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert load_leads_directory(tmp_path) == []

    def test_invalid_file_in_directory_raises(self, tmp_path):
        (tmp_path / "good.json").write_text(
            json.dumps([{"company": "Acme Roofing", "phone": "5550101001"}]),
            encoding="utf-8",
        )
        (tmp_path / "bad.json").write_text("{broken", encoding="utf-8")

        with pytest.raises(LeadLoadError):
            load_leads_directory(tmp_path)
