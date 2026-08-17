from typing import Any, Dict, Optional

from .crm_db import CrmDatabase
from .crm_dial import DIALABLE_STATUSES
from .crm_outcomes import OUTCOME_STATUS_MAP
from .crm_region import _PHONE_AREA_CODE_SQL, area_codes_for_region

# Statuses shown in analytics (zeros when none match)
LEAD_STATUSES = tuple(
    dict.fromkeys(("new", "callback") + tuple(OUTCOME_STATUS_MAP.values()))
)

# Outcome codes shown in analytics (zeros when none match)
OUTCOME_CODES = tuple(OUTCOME_STATUS_MAP.keys())


def _empty_status_counts() -> Dict[str, Any]:
    by_status = {status: 0 for status in LEAD_STATUSES}
    return {
        "total": 0,
        "queue": 0,
        "by_status": by_status,
    }


def lead_status_counts(
    db: CrmDatabase,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Count leads by current status, optionally filtered by location

    Includes every lead in scope, not only dialable statuses.

    Args:
        db: CRM database instance
        region: Optional location filter ('bc', 'on'); None = full list

    Returns:
        Dict with total, queue (new + callback), and by_status counts
    """
    area_codes = area_codes_for_region(region)
    if area_codes is not None and not area_codes:
        return _empty_status_counts()

    region_clause = ""
    region_params: tuple = ()
    if area_codes is not None:
        area_placeholders = ", ".join("?" for _ in area_codes)
        region_clause = f" WHERE {_PHONE_AREA_CODE_SQL} IN ({area_placeholders})"
        region_params = area_codes

    sql = (
        f"SELECT status, COUNT(*) AS n FROM leads"
        f"{region_clause} GROUP BY status"
    )

    with db.connect() as conn:
        rows = conn.execute(sql, region_params).fetchall()

    result = _empty_status_counts()
    by_status = result["by_status"]
    total = 0
    for row in rows:
        status = row["status"]
        count = int(row["n"])
        total += count
        by_status[status] = by_status.get(status, 0) + count

    result["total"] = total
    result["queue"] = sum(by_status.get(status, 0) for status in DIALABLE_STATUSES)
    return result


def _empty_outcome_counts() -> Dict[str, Any]:
    return {
        "total": 0,
        "by_outcome": {code: 0 for code in OUTCOME_CODES},
    }


def outcome_counts(
    db: CrmDatabase,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Count logged call outcomes, optionally filtered by lead location

    Each call_outcomes row counts once. Location uses the lead's phone.

    Args:
        db: CRM database instance
        region: Optional location filter ('bc', 'on'); None = full list

    Returns:
        Dict with total and by_outcome counts
    """
    area_codes = area_codes_for_region(region)
    if area_codes is not None and not area_codes:
        return _empty_outcome_counts()

    if area_codes is None:
        sql = "SELECT outcome, COUNT(*) AS n FROM call_outcomes GROUP BY outcome"
        params: tuple = ()
    else:
        phone_sql = _PHONE_AREA_CODE_SQL.replace("phone", "leads.phone")
        area_placeholders = ", ".join("?" for _ in area_codes)
        sql = (
            "SELECT call_outcomes.outcome AS outcome, COUNT(*) AS n "
            "FROM call_outcomes "
            "INNER JOIN leads ON leads.id = call_outcomes.lead_id "
            f"WHERE {phone_sql} IN ({area_placeholders}) "
            "GROUP BY call_outcomes.outcome"
        )
        params = area_codes

    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = _empty_outcome_counts()
    by_outcome = result["by_outcome"]
    total = 0
    for row in rows:
        code = row["outcome"]
        count = int(row["n"])
        total += count
        by_outcome[code] = by_outcome.get(code, 0) + count

    result["total"] = total
    return result


def ratio_bar(count: int, total: int, width: int = 12) -> str:
    """
    Build a fixed-width bar for count / total

    Uses filled and empty block characters. Empty or zero totals
    render as all empty. Values are clamped to the bar width.

    Args:
        count: Portion to fill
        total: Denominator
        width: Bar width in characters

    Returns:
        String of length width (empty string if width <= 0)
    """
    if width <= 0:
        return ""

    if total <= 0 or count <= 0:
        filled = 0
    else:
        filled = round((count / total) * width)
        if filled < 0:
            filled = 0
        if filled > width:
            filled = width

    return ("█" * filled) + ("░" * (width - filled))
