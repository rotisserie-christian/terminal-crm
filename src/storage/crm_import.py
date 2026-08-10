import logging
from pathlib import Path
from typing import Any, Dict, Union

from src.utils.exceptions import LeadLoadError

from .crm_db import CrmDatabase
from .crm_json import DEFAULT_LEADS_DIR, list_lead_files, load_leads_file
from .crm_leads import merge_leads

logger = logging.getLogger(__name__)


def import_leads_from_directory(
    db: CrmDatabase,
    leads_dir: Union[str, Path] = DEFAULT_LEADS_DIR,
) -> Dict[str, Any]:
    """
    Load lead JSON files from a directory and merge them into the CRM database

    Processes each *.json file independently so one bad file does not block others.

    Args:
        db: CRM database instance
        leads_dir: Directory containing lead JSON files

    Returns:
        Summary dict with:
        - added / updated / skipped: merge counts
        - files: number of JSON files successfully processed
        - loaded: total lead objects loaded from successful files
        - errors: list of {file, error} for files that failed to load
    """
    summary: Dict[str, Any] = {
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "files": 0,
        "loaded": 0,
        "errors": [],
    }

    files = list_lead_files(leads_dir)
    if not files:
        logger.info(f"No lead JSON files found in {leads_dir}")
        return summary

    for path in files:
        try:
            leads = load_leads_file(path)
        except (LeadLoadError, OSError) as e:
            logger.warning(f"Skipping lead file {path.name}: {e}")
            summary["errors"].append({"file": path.name, "error": str(e)})
            continue

        result = merge_leads(db, leads)
        summary["added"] += result["added"]
        summary["updated"] += result["updated"]
        summary["skipped"] += result["skipped"]
        summary["files"] += 1
        summary["loaded"] += len(leads)

    logger.info(
        "Lead import complete: files=%s loaded=%s added=%s updated=%s skipped=%s errors=%s",
        summary["files"],
        summary["loaded"],
        summary["added"],
        summary["updated"],
        summary["skipped"],
        len(summary["errors"]),
    )
    return summary
