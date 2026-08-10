import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from .crm_db import CrmDatabase

logger = logging.getLogger(__name__)


def normalize_phone(phone: Any) -> Optional[str]:
    """
    Normalize a phone value to digits only for storage and dedupe

    Args:
        phone: Raw phone value from JSON or user input

    Returns:
        Digits-only phone string, or None if no digits are present
    """
    if phone is None:
        return None

    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def to_bool_int(value: Any) -> int:
    """
    Coerce a value to an integer boolean (0 or 1)

    Accepts bools, numbers, and common string forms (true/false, yes/no, 1/0).
    """
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return 1 if value else 0

    if value is None:
        return 0

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return 1
    if text in {"0", "false", "no", "n", ""}:
        return 0

    return 0


def _text(value: Any) -> str:
    """Coerce a value to a trimmed string (empty if missing)."""
    if value is None:
        return ""
    return str(value).strip()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_lead_on_connection(
    conn,
    lead: Mapping[str, Any],
) -> str:
    """
    Insert or update a single lead using an open DB connection

    Returns:
        'added', 'updated', or 'skipped'
    """
    phone = normalize_phone(lead.get("phone"))
    if not phone:
        logger.debug("Skipping lead with missing/invalid phone")
        return "skipped"

    company = _text(lead.get("company"))
    website = _text(lead.get("website"))
    trade = _text(lead.get("trade"))
    signals = _text(lead.get("signals"))
    hiring = _text(lead.get("hiring"))
    is_hiring = to_bool_int(lead.get("is_hiring"))
    has_ads = to_bool_int(lead.get("has_ads"))
    now = _utcnow()

    existing = conn.execute(
        "SELECT id FROM leads WHERE phone = ?",
        (phone,),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE leads
            SET company = ?,
                website = ?,
                trade = ?,
                signals = ?,
                hiring = ?,
                is_hiring = ?,
                has_ads = ?,
                updated_at = ?
            WHERE phone = ?
            """,
            (
                company,
                website,
                trade,
                signals,
                hiring,
                is_hiring,
                has_ads,
                now,
                phone,
            ),
        )
        return "updated"

    conn.execute(
        """
        INSERT INTO leads (
            company, website, trade, signals, hiring, phone,
            is_hiring, has_ads, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
        """,
        (
            company,
            website,
            trade,
            signals,
            hiring,
            phone,
            is_hiring,
            has_ads,
            now,
            now,
        ),
    )
    return "added"


def upsert_lead(db: CrmDatabase, lead: Mapping[str, Any]) -> str:
    """
    Insert a new lead or update an existing one matched by normalized phone

    Preserves status and created_at on update. Skips leads with no usable phone.

    Args:
        db: CRM database instance
        lead: Lead field mapping

    Returns:
        'added', 'updated', or 'skipped'
    """
    with db.connect() as conn:
        return _upsert_lead_on_connection(conn, lead)


def merge_leads(db: CrmDatabase, leads: List[Mapping[str, Any]]) -> Dict[str, int]:
    """
    Merge a list of leads into the CRM database

    Args:
        db: CRM database instance
        leads: Lead field mappings

    Returns:
        Summary counts: {'added': n, 'updated': n, 'skipped': n}
    """
    summary = {"added": 0, "updated": 0, "skipped": 0}

    with db.connect() as conn:
        for lead in leads:
            if not isinstance(lead, Mapping):
                summary["skipped"] += 1
                continue

            result = _upsert_lead_on_connection(conn, lead)
            summary[result] += 1

    logger.info(
        "Lead merge complete: added=%s updated=%s skipped=%s",
        summary["added"],
        summary["updated"],
        summary["skipped"],
    )
    return summary
