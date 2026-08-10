import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from src.utils.exceptions import CrmDbError

from .crm_db import CrmDatabase

logger = logging.getLogger(__name__)

# Leads in these statuses are eligible for the dial queue
DIALABLE_STATUSES = ("callback", "new")

# Dial outcome codes -> lead status after logging
OUTCOME_STATUS_MAP = {
    "vm": "new",
    "no_answer": "new",
    "cb": "callback",
    "ni": "not_interested",
    "wn": "wrong_number",
    "closed": "closed",
}

# Human-readable labels for the dial outcome menu (label, code)
OUTCOME_MENU_CHOICES = (
    ("Voicemail", "vm"),
    ("No answer", "no_answer"),
    ("Callback", "cb"),
    ("Not interested", "ni"),
    ("Wrong number", "wn"),
    ("Closed / Won", "closed"),
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_next_dial_lead(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
) -> Optional[Dict[str, Any]]:
    """
    Fetch the next lead to dial from the CRM database

    Priority:
    1. status = 'callback' before 'new' (and any other dialable statuses)
    2. oldest updated_at (recently dialed leads rotate to the back)
    3. lowest id as a tiebreaker

    Args:
        db: CRM database instance
        statuses: Status values considered dialable

    Returns:
        Lead as a plain dict, or None if the dial queue is empty
    """
    if not statuses:
        return None

    placeholders = ", ".join("?" for _ in statuses)
    # Prefer callback over new when both are dialable
    priority_cases = " ".join(
        f"WHEN ? THEN {index}" for index, _ in enumerate(statuses)
    )

    sql = f"""
        SELECT
            id,
            company,
            website,
            trade,
            signals,
            hiring,
            phone,
            is_hiring,
            has_ads,
            status,
            created_at,
            updated_at
        FROM leads
        WHERE status IN ({placeholders})
        ORDER BY
            CASE status
                {priority_cases}
                ELSE {len(statuses)}
            END,
            updated_at ASC,
            id ASC
        LIMIT 1
    """

    params = tuple(statuses) + tuple(statuses)

    with db.connect() as conn:
        row = conn.execute(sql, params).fetchone()

    if row is None:
        logger.debug("Dial queue empty")
        return None

    lead = dict(row)
    logger.debug(
        "Next dial lead id=%s phone=%s status=%s",
        lead.get("id"),
        lead.get("phone"),
        lead.get("status"),
    )
    return lead


def count_dialable_leads(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
) -> int:
    """
    Count leads currently in the dial queue

    Args:
        db: CRM database instance
        statuses: Status values considered dialable

    Returns:
        Number of dialable leads
    """
    if not statuses:
        return 0

    placeholders = ", ".join("?" for _ in statuses)
    sql = f"SELECT COUNT(*) AS n FROM leads WHERE status IN ({placeholders})"

    with db.connect() as conn:
        row = conn.execute(sql, tuple(statuses)).fetchone()

    return int(row["n"])


def log_call_outcome(
    db: CrmDatabase,
    lead_id: int,
    outcome: str,
    description: str = "",
) -> Dict[str, Any]:
    """
    Log a call outcome and update the lead's current status

    Inserts a row into call_outcomes and sets leads.status from OUTCOME_STATUS_MAP.
    Always bumps updated_at so the lead rotates in the dial queue when still dialable.

    Args:
        db: CRM database instance
        lead_id: Lead primary key
        outcome: Outcome code (vm, cb, ni, wn, closed, no_answer)
        description: Optional free-text notes

    Returns:
        Dict with lead_id, outcome, status, and description

    Raises:
        ValueError: If outcome is unknown
        CrmDbError: If the lead does not exist
    """
    code = str(outcome).strip().lower()
    if code not in OUTCOME_STATUS_MAP:
        known = ", ".join(sorted(OUTCOME_STATUS_MAP))
        raise ValueError(f"Unknown outcome '{outcome}'. Expected one of: {known}")

    new_status = OUTCOME_STATUS_MAP[code]
    notes = description if description is not None else ""
    notes = str(notes).strip()
    now = _utcnow()

    try:
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM leads WHERE id = ?",
                (lead_id,),
            ).fetchone()
            if existing is None:
                raise CrmDbError(f"Lead not found: id={lead_id}")

            conn.execute(
                """
                INSERT INTO call_outcomes (lead_id, outcome, description, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (lead_id, code, notes, now),
            )
            conn.execute(
                """
                UPDATE leads
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_status, now, lead_id),
            )
    except CrmDbError:
        raise
    except Exception as e:
        logger.error(f"Failed to log call outcome: {e}", exc_info=True)
        raise CrmDbError(f"Failed to log call outcome: {e}") from e

    logger.info(
        "Logged outcome lead_id=%s outcome=%s status=%s",
        lead_id,
        code,
        new_status,
    )
    return {
        "lead_id": lead_id,
        "outcome": code,
        "status": new_status,
        "description": notes,
    }
