import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from src.utils.exceptions import LeadLoadError

logger = logging.getLogger(__name__)

DEFAULT_LEADS_DIR = "leads"


def _extract_lead_list(payload: Any, source_name: str) -> List[Any]:
    """
    Extract a lead list from parsed JSON

    Accepts a top-level array, or an object with a "leads" array.
    """
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict) and isinstance(payload.get("leads"), list):
        return payload["leads"]

    raise LeadLoadError(
        f"Invalid lead file format in {source_name}: "
        f"expected a list or an object with a 'leads' list"
    )


def _validate_lead_items(items: List[Any], source_name: str) -> List[Dict[str, Any]]:
    """Ensure every lead entry is an object/dict."""
    leads: List[Dict[str, Any]] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise LeadLoadError(
                f"Invalid lead entry in {source_name} at index {i}: "
                f"expected object, got {type(item).__name__}"
            )
        leads.append(item)

    return leads


def load_leads_file(filepath: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Load leads from a single JSON file

    Supported shapes:
    - [ {lead}, {lead}, ... ]
    - { "leads": [ {lead}, ... ] }

    Returns:
        List of lead dictionaries (field coercion happens at merge time)

    Raises:
        FileNotFoundError: If the file does not exist
        LeadLoadError: If the file cannot be read or is invalid
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Lead file not found: {path.name}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        items = _extract_lead_list(payload, path.name)
        leads = _validate_lead_items(items, path.name)

        logger.info(
            "Leads loaded successfully",
            extra={"lead_filename": path.name, "num_leads": len(leads)},
        )
        return leads

    except LeadLoadError:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path.name}: {e}", exc_info=True)
        raise LeadLoadError(f"Lead file is corrupted: {e}") from e
    except PermissionError as e:
        logger.error(f"Permission denied reading {path}")
        raise LeadLoadError("Cannot read lead file: Permission denied") from e
    except OSError as e:
        logger.error(f"OS error loading leads: {e}", exc_info=True)
        raise LeadLoadError(f"Failed to load lead file: {e}") from e


def list_lead_files(leads_dir: Union[str, Path] = DEFAULT_LEADS_DIR) -> List[Path]:
    """
    List JSON lead files in a directory (sorted by name)

    Skips non-files. Does not create the directory.
    """
    directory = Path(leads_dir)

    if not directory.exists():
        return []

    if not directory.is_dir():
        raise LeadLoadError(f"Leads path is not a directory: {directory}")

    return sorted(
        path for path in directory.glob("*.json") if path.is_file()
    )


def load_leads_directory(
    leads_dir: Union[str, Path] = DEFAULT_LEADS_DIR,
) -> List[Dict[str, Any]]:
    """
    Load and concatenate leads from all *.json files in a directory

    Returns:
        Combined list of lead dictionaries from every JSON file found

    Raises:
        LeadLoadError: If any file is invalid
    """
    files = list_lead_files(leads_dir)
    if not files:
        logger.info(f"No lead JSON files found in {leads_dir}")
        return []

    all_leads: List[Dict[str, Any]] = []
    for path in files:
        all_leads.extend(load_leads_file(path))

    logger.info(
        "Loaded leads from directory",
        extra={"leads_dir": str(leads_dir), "num_files": len(files), "num_leads": len(all_leads)},
    )
    return all_leads
