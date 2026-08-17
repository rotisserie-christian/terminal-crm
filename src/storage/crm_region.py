from typing import Any, Dict, Optional, Set, Tuple

# Geographic NANP area codes by dial-filter region (expand as needed)
REGION_AREA_CODES: Dict[str, Set[str]] = {
    "bc": {"236", "250", "257", "604", "672", "778"},
    "on": {
        "226",
        "249",
        "289",
        "343",
        "365",
        "382",
        "416",
        "437",
        "519",
        "548",
        "613",
        "647",
        "683",
        "705",
        "742",
        "753",
        "807",
        "905",
        "942",
    },
}

# Non-geographic toll-free NPAs — never match a location filter
TOLL_FREE_AREA_CODES: Set[str] = {
    "800",
    "822",
    "833",
    "844",
    "855",
    "866",
    "877",
    "880",
    "881",
    "882",
    "883",
    "884",
    "885",
    "886",
    "887",
    "888",
    "889",
}

# SQL expression: NANP area code from a digits-only phone column
_PHONE_AREA_CODE_SQL = """
CASE
    WHEN length(phone) = 11 AND phone LIKE '1%' THEN substr(phone, 2, 3)
    WHEN length(phone) >= 10 THEN substr(phone, 1, 3)
    ELSE NULL
END
""".strip()


def phone_area_code(phone: Any) -> Optional[str]:
    """
    Extract the NANP area code from a digits-only (or raw) phone value

    Args:
        phone: Stored or raw phone string

    Returns:
        Three-digit area code, or None if it cannot be determined
    """
    if phone is None:
        return None

    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:4]
    if len(digits) >= 10:
        return digits[:3]
    return None


def area_codes_for_region(region: Optional[str]) -> Optional[Tuple[str, ...]]:
    """
    Resolve a dial-filter region key to its geographic area codes

    Toll-free NPAs are never included. Unknown keys raise ValueError.

    Args:
        region: Region key ('bc', 'on'), or None for no location filter

    Returns:
        Sorted tuple of area codes, or None when region is None/blank
    """
    if region is None:
        return None

    key = str(region).strip().lower()
    if not key:
        return None

    codes = REGION_AREA_CODES.get(key)
    if codes is None:
        known = ", ".join(sorted(REGION_AREA_CODES))
        raise ValueError(f"Unknown dial region '{region}'. Expected one of: {known}")

    # Defensive: never treat toll-free as geographic even if misconfigured
    geographic = sorted(code for code in codes if code not in TOLL_FREE_AREA_CODES)
    return tuple(geographic)
