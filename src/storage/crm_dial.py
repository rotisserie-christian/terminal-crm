import logging
from typing import Any, Dict, Optional, Sequence

from .crm_db import CrmDatabase

logger = logging.getLogger(__name__)

# Leads in these statuses are eligible for the dial queue
DIALABLE_STATUSES = ("callback", "new")


def get_next_dial_lead(
    db: CrmDatabase,
    statuses: Sequence[str] = DIALABLE_STATUSES,
) -> Optional[Dict[str, Any]]:
    """
    Fetch the next lead to dial from the CRM database

    Priority:
    1. status = 'callback' before 'new' (and any other dialable statuses)
    2. oldest created_at
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
            created_at ASC,
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
