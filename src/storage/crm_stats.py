from typing import Any, Dict, Optional

from .crm_db import CrmDatabase
from .crm_dial import DIALABLE_STATUSES
from .crm_outcomes import OUTCOME_STATUS_MAP
from .crm_region import _PHONE_AREA_CODE_SQL, area_codes_for_region

# Statuses shown in analytics (zeros when none match)
LEAD_STATUSES = tuple(
    dict.fromkeys(("new", "callback") + tuple(OUTCOME_STATUS_MAP.values()))
)


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
