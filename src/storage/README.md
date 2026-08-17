### /src/storage
- `manager.py` - Orchestrates chat persistence and directory management
- `file_io.py` - Pure file operations, validation, and naming logic for chats
- `crm_db.py` - SQLite CRM database bootstrap (leads + call_outcomes schema)
- `crm_leads.py` - Phone normalization and lead upsert/merge into SQLite
- `crm_json.py` - Load and validate lead lists from JSON files
- `crm_import.py` - Import orchestration: load JSON leads and merge into SQLite
- `crm_region.py` - Dial location filter (NANP area codes, toll-free exclusion)
- `crm_outcomes.py` - Call outcome maps and logging
- `crm_dial.py` - Dial queue helpers (list/next/count, index navigation)
- `crm_stats.py` - Lead status analytics counts

