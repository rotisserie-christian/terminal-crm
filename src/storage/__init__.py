"""
Storage module

Manages chat persistence, CRM database, and file organization
"""

from .manager import ChatStorage
from .file_io import save_chat_file, load_chat_file
from .crm_db import CrmDatabase
from .crm_leads import normalize_phone, upsert_lead, merge_leads
from .crm_json import load_leads_file, load_leads_directory, list_lead_files
from .crm_import import import_leads_from_directory
from .crm_dial import (
    list_dialable_leads,
    get_next_dial_lead,
    clamp_dial_index,
    step_dial_index,
    can_step_dial_previous,
    can_step_dial_next,
    count_dialable_leads,
    count_leads,
    log_call_outcome,
    phone_area_code,
    area_codes_for_region,
    DIALABLE_STATUSES,
    OUTCOME_STATUS_MAP,
    OUTCOME_MENU_CHOICES,
    REGION_AREA_CODES,
    TOLL_FREE_AREA_CODES,
)
