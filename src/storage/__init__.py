"""
Storage module

Manages chat persistence, CRM database, and file organization
"""

from .manager import ChatStorage
from .file_io import save_chat_file, load_chat_file
from .crm_db import CrmDatabase
from .crm_leads import normalize_phone, upsert_lead, merge_leads
