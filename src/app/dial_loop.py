import logging

import questionary

from src.storage import (
    CrmDatabase,
    count_dialable_leads,
    get_next_dial_lead,
    log_call_outcome,
)
from src.ui import TerminalUI
from src.utils.exceptions import CrmDbError


logger = logging.getLogger(__name__)


class DialLoop:
    """
    Handles the dial interaction loop

    Responsibilities:
    - Fetch the next dialable lead
    - Display lead details
    - Prompt for outcome + description
    - Persist outcome and advance
    """

    def __init__(self, ui: TerminalUI, crm_db: CrmDatabase):
        """
        Initialize dial loop

        Args:
            ui: Terminal UI instance
            crm_db: CRM database instance
        """
        self.ui = ui
        self.crm_db = crm_db

    def run(self) -> None:
        """
        Run the dial loop until the queue is empty or the user goes back
        """
        while True:
            remaining = count_dialable_leads(self.crm_db)
            lead = get_next_dial_lead(self.crm_db)

            if lead is None:
                self.ui.clear_screen()
                self.ui.display_system_message(
                    "Dial queue is empty. Import leads or set callbacks, then try again."
                )
                questionary.press_any_key_to_continue().ask()
                return

            self.ui.clear_screen()
            self.ui.display_dial_lead(lead, remaining=remaining)

            result = self.ui.prompt_call_outcome()
            if result is None:
                self.ui.display_system_message("Returning to menu...")
                return

            try:
                logged = log_call_outcome(
                    self.crm_db,
                    lead_id=lead["id"],
                    outcome=result["outcome"],
                    description=result.get("description", ""),
                )
            except (CrmDbError, ValueError) as e:
                logger.error(f"Failed to log dial outcome: {e}", exc_info=True)
                self.ui.display_error(str(e))
                questionary.press_any_key_to_continue().ask()
                return

            self.ui.display_system_message(
                f"Logged {logged['outcome']} → status {logged['status']}"
            )
