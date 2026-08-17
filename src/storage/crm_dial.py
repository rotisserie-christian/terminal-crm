import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.utils.exceptions import CrmDbError

from .crm_db import CrmDatabase
from .crm_region import _PHONE_AREA_CODE_SQL, area_codes_for_region

logger = logging.getLogger(__name__)

# Leads in these statuses are eligible for the dial queue
DIALABLE_STATUSES = ("callback", "new")

# Dial outcome codes -> lead status after logging
OUTCOME_STATUS_MAP = {
    "vm": "new",
    "no_answer": "new",
    "cb": "callback",
    "ni": "not_interested",
    "dnc": "do_not_call",
    "wn": "wrong_number",
    "closed": "closed",
}

# Human-readable labels for the dial outcome menu (label, code)
OUTCOME_MENU_CHOICES = (
    ("Voicemail", "vm"),
    ("No answer", "no_answer"),
    ("Callback", "cb"),
    ("Not interested", "ni"),
    ("Do not call", "dnc"),
    ("Wrong number", "wn"),
    ("Closed / Won", "closed"),
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_dialable_leads(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
    region: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all dialable leads in queue order

    Priority:
    1. status = 'callback' before 'new' (and any other dialable statuses)
    2. oldest updated_at (recently dialed leads rotate to the back)
    3. lowest id as a tiebreaker

    Args:
        db: CRM database instance
        statuses: Status values considered dialable
        region: Optional location filter ('bc', 'on'); None = full list

    Returns:
        Dialable leads as plain dicts, empty if the queue is empty
    """
    if not statuses:
        return []

    area_codes = area_codes_for_region(region)
    if area_codes is not None and not area_codes:
        return []

    placeholders = ", ".join("?" for _ in statuses)
    # Prefer callback over new when both are dialable
    priority_cases = " ".join(
        f"WHEN ? THEN {index}" for index, _ in enumerate(statuses)
    )

    region_clause = ""
    region_params: Tuple[str, ...] = ()
    if area_codes is not None:
        area_placeholders = ", ".join("?" for _ in area_codes)
        region_clause = f" AND {_PHONE_AREA_CODE_SQL} IN ({area_placeholders})"
        region_params = area_codes

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
        WHERE status IN ({placeholders}){region_clause}
        ORDER BY
            CASE status
                {priority_cases}
                ELSE {len(statuses)}
            END,
            updated_at ASC,
            id ASC
    """

    params = tuple(statuses) + region_params + tuple(statuses)

    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    leads = [dict(row) for row in rows]
    logger.debug("Listed %s dialable leads region=%s", len(leads), region)
    return leads


def get_next_dial_lead(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
    region: Optional[str] = None,
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
        region: Optional location filter ('bc', 'on'); None = full list

    Returns:
        Lead as a plain dict, or None if the dial queue is empty
    """
    leads = list_dialable_leads(db, statuses=statuses, region=region)
    if not leads:
        logger.debug("Dial queue empty region=%s", region)
        return None

    lead = leads[0]
    logger.debug(
        "Next dial lead id=%s phone=%s status=%s region=%s",
        lead.get("id"),
        lead.get("phone"),
        lead.get("status"),
        region,
    )
    return lead


def clamp_dial_index(index: int, count: int) -> int:
    """
    Keep a dial-queue index inside the list

    Empty queues stay at 0. Does not wrap.

    Args:
        index: Current or requested position
        count: Number of leads in the queue

    Returns:
        Index in [0, count), or 0 when the queue is empty
    """
    if count <= 0:
        return 0
    if index < 0:
        return 0
    last = count - 1
    if index > last:
        return last
    return index


def step_dial_index(index: int, delta: int, count: int) -> int:
    """
    Move one step in the dial queue without wrapping

    Args:
        index: Current position
        delta: Direction (-1 previous, +1 next)
        count: Number of leads in the queue

    Returns:
        Clamped index. Empty queues stay at 0.
    """
    return clamp_dial_index(index + delta, count)


def can_step_dial_previous(index: int) -> bool:
    """True when Previous should be enabled."""
    return index > 0


def can_step_dial_next(index: int, count: int) -> bool:
    """True when Next should be enabled."""
    return count > 0 and index < count - 1


def count_dialable_leads(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
    region: Optional[str] = None,
) -> int:
    """
    Count leads currently in the dial queue

    Args:
        db: CRM database instance
        statuses: Status values considered dialable
        region: Optional location filter ('bc', 'on'); None = full list

    Returns:
        Number of dialable leads
    """
    if not statuses:
        return 0

    area_codes = area_codes_for_region(region)
    if area_codes is not None and not area_codes:
        return 0

    placeholders = ", ".join("?" for _ in statuses)
    region_clause = ""
    region_params: Tuple[str, ...] = ()
    if area_codes is not None:
        area_placeholders = ", ".join("?" for _ in area_codes)
        region_clause = f" AND {_PHONE_AREA_CODE_SQL} IN ({area_placeholders})"
        region_params = area_codes

    sql = (
        f"SELECT COUNT(*) AS n FROM leads "
        f"WHERE status IN ({placeholders}){region_clause}"
    )

    with db.connect() as conn:
        row = conn.execute(sql, tuple(statuses) + region_params).fetchone()

    return int(row["n"])


def count_leads(db: CrmDatabase) -> int:
    """
    Count all leads in the CRM database

    Args:
        db: CRM database instance

    Returns:
        Total number of leads
    """
    with db.connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()
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
        outcome: Outcome code (vm, cb, ni, dnc, wn, closed, no_answer)
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
