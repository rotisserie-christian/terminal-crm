import logging

import questionary

from src.storage import (
    CrmDatabase,
    count_dialable_leads,
    count_leads,
    get_next_dial_lead,
    log_call_outcome,
)
from src.ui import TerminalUI
from src.ui.terminal import ansi_clear, print_plain, show_cursor, sync_after_rich
from src.utils.exceptions import CrmDbError


logger = logging.getLogger(__name__)

_REGION_LABELS = {
    "bc": "BC",
    "on": "Ontario",
}


class DialLoop:
    """
    Handles the dial interaction loop

    Responsibilities:
    - Prompt for optional location filter
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

    def _press_any_key(self) -> None:
        sync_after_rich(self.ui.console)
        show_cursor()
        questionary.press_any_key_to_continue().ask()

    def _show_empty_queue_and_exit(self, region=None) -> None:
        """Explain why dial cannot continue, then return to the menu."""
        ansi_clear()
        total = count_leads(self.crm_db)
        if total == 0:
            print_plain("No leads in the CRM yet.")
            print_plain(
                "Use Add Leads to import a JSON list from /leads "
                "(see leads/sample.json), then choose Dial again."
            )
        elif region:
            label = _REGION_LABELS.get(region, region)
            print_plain(f"No dialable {label} leads right now.")
            full_count = count_dialable_leads(self.crm_db)
            if full_count > 0:
                print_plain(
                    f"{full_count} dialable lead(s) exist outside this filter. "
                    "Try Full list, or import more leads for this location."
                )
            else:
                print_plain(
                    f"{total} lead(s) are in the database, but none have status "
                    "'new' or 'callback'. Import more leads or wait for callbacks."
                )
        else:
            print_plain("No dialable leads right now.")
            print_plain(
                f"{total} lead(s) are in the database, but none have status "
                "'new' or 'callback'. Import more leads or wait for callbacks."
            )
        print_plain("")
        self._press_any_key()

    def run(self) -> None:
        """
        Run the dial loop until the queue is empty or the user goes back
        """
        filter_choice = self.ui.prompt_dial_filter()
        if filter_choice is None:
            self.ui.display_system_message("Returning to menu...")
            return

        region = filter_choice.get("region")

        while True:
            ansi_clear()
            with self.ui.status("Loading next lead..."):
                remaining = count_dialable_leads(self.crm_db, region=region)
                lead = get_next_dial_lead(self.crm_db, region=region)

            if lead is None:
                self._show_empty_queue_and_exit(region=region)
                return

            # prompt_call_outcome owns the screen (plain dial card + menu)
            result = self.ui.prompt_call_outcome(lead=lead, remaining=remaining)
            if result is None:
                self.ui.display_system_message("Returning to menu...")
                return

            try:
                with self.ui.status("Saving outcome..."):
                    logged = log_call_outcome(
                        self.crm_db,
                        lead_id=lead["id"],
                        outcome=result["outcome"],
                        description=result.get("description", ""),
                    )
            except (CrmDbError, ValueError) as e:
                logger.error(f"Failed to log dial outcome: {e}", exc_info=True)
                self.ui.display_error(str(e))
                self._press_any_key()
                return

            self.ui.display_system_message(
                f"Logged {logged['outcome']} → status {logged['status']}"
            )
