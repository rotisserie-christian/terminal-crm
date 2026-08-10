import json

from src.storage import CrmDatabase, import_leads_from_directory


class TestImportLeadsFromDirectory:

    def test_imports_leads_from_json_files(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()
        (leads_dir / "sample.json").write_text(
            json.dumps(
                [
                    {
                        "company": "Acme Roofing",
                        "phone": "5550101001",
                        "is_hiring": True,
                        "has_ads": True,
                    },
                    {
                        "company": "Blue Sky HVAC",
                        "phone": "5550101002",
                        "is_hiring": False,
                        "has_ads": False,
                    },
                ]
            ),
            encoding="utf-8",
        )

        db = CrmDatabase(str(tmp_path / "crm.db"))
        summary = import_leads_from_directory(db, leads_dir)

        assert summary["added"] == 2
        assert summary["updated"] == 0
        assert summary["skipped"] == 0
        assert summary["files"] == 1
        assert summary["loaded"] == 2
        assert summary["errors"] == []

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        assert count == 2

    def test_reimport_updates_existing_by_phone(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()
        (leads_dir / "leads.json").write_text(
            json.dumps(
                [
                    {"company": "Acme Roofing", "phone": "5550101001", "trade": "roofing"},
                ]
            ),
            encoding="utf-8",
        )

        db = CrmDatabase(str(tmp_path / "crm.db"))
        first = import_leads_from_directory(db, leads_dir)
        assert first["added"] == 1

        (leads_dir / "leads.json").write_text(
            json.dumps(
                [
                    {
                        "company": "Acme Roofing LLC",
                        "phone": "555-010-1001",
                        "trade": "commercial roofing",
                    },
                    {"company": "Pine Plumbing", "phone": "5550101003"},
                ]
            ),
            encoding="utf-8",
        )

        second = import_leads_from_directory(db, leads_dir)

        assert second == {
            "added": 1,
            "updated": 1,
            "skipped": 0,
            "files": 1,
            "loaded": 2,
            "errors": [],
        }

        with db.connect() as conn:
            row = conn.execute(
                "SELECT company, trade FROM leads WHERE phone = ?",
                ("5550101001",),
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]

        assert count == 2
        assert row["company"] == "Acme Roofing LLC"
        assert row["trade"] == "commercial roofing"

    def test_counts_skipped_leads_without_phone(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()
        (leads_dir / "leads.json").write_text(
            json.dumps(
                [
                    {"company": "Acme Roofing", "phone": "5550101001"},
                    {"company": "No Phone", "phone": ""},
                    {"company": "Also Bad", "phone": None},
                ]
            ),
            encoding="utf-8",
        )

        db = CrmDatabase(str(tmp_path / "crm.db"))
        summary = import_leads_from_directory(db, leads_dir)

        assert summary["added"] == 1
        assert summary["skipped"] == 2
        assert summary["loaded"] == 3
        assert summary["errors"] == []

    def test_continues_when_one_file_is_corrupt(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()
        (leads_dir / "good.json").write_text(
            json.dumps([{"company": "Acme Roofing", "phone": "5550101001"}]),
            encoding="utf-8",
        )
        (leads_dir / "bad.json").write_text("{broken", encoding="utf-8")

        db = CrmDatabase(str(tmp_path / "crm.db"))
        summary = import_leads_from_directory(db, leads_dir)

        assert summary["added"] == 1
        assert summary["files"] == 1
        assert summary["loaded"] == 1
        assert len(summary["errors"]) == 1
        assert summary["errors"][0]["file"] == "bad.json"
        assert "corrupted" in summary["errors"][0]["error"]

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        assert count == 1

    def test_empty_directory_returns_zero_summary(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()

        db = CrmDatabase(str(tmp_path / "crm.db"))
        summary = import_leads_from_directory(db, leads_dir)

        assert summary == {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "files": 0,
            "loaded": 0,
            "errors": [],
        }

    def test_aggregates_across_multiple_files(self, tmp_path):
        leads_dir = tmp_path / "leads"
        leads_dir.mkdir()
        (leads_dir / "a.json").write_text(
            json.dumps([{"company": "Acme Roofing", "phone": "5550101001"}]),
            encoding="utf-8",
        )
        (leads_dir / "b.json").write_text(
            json.dumps({"leads": [{"company": "Blue Sky HVAC", "phone": "5550101002"}]}),
            encoding="utf-8",
        )

        db = CrmDatabase(str(tmp_path / "crm.db"))
        summary = import_leads_from_directory(db, leads_dir)

        assert summary["added"] == 2
        assert summary["files"] == 2
        assert summary["loaded"] == 2
        assert summary["errors"] == []
