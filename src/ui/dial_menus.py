import time

import pyperclip
import questionary

from src.storage.crm_outcomes import OUTCOME_MENU_CHOICES
from .terminal import ansi_clear, print_plain


class DialMenuMixin:
    """Dial browse and call-outcome prompts (expects MenuManager helpers)."""

    def prompt_dial_actions(
        self,
        lead=None,
        remaining=None,
        can_previous=False,
        can_next=False,
    ):
        """
        Prompt to browse the dial queue or edit the current lead

        Draws the dial lead Panel, then Previous / Next / Edit.
        Edit opens the existing call-outcome menu. Back from that menu
        returns here.

        Args:
            lead: Lead dict for the card and nested outcome menu
            remaining: Optional dialable queue count for the card header
            can_previous: When False, Previous is disabled
            can_next: When False, Next is disabled

        Returns:
            Dict with 'action' of 'previous', 'next', or 'outcome'
            (outcome includes 'outcome' and 'description'),
            or None if cancelled/back
        """
        lead = lead or {}
        back_label = "< Back>"

        while True:
            ansi_clear()
            if lead:
                self.display.display_dial_lead(lead, remaining=remaining)

            choices = [
                questionary.Choice(
                    title="Previous",
                    value="previous",
                    disabled=False if can_previous else "Already at first lead",
                ),
                questionary.Choice(
                    title="Next",
                    value="next",
                    disabled=False if can_next else "Already at last lead",
                ),
                questionary.Choice("Edit", value="edit"),
                back_label,
            ]

            choice = self._show_menu("Dial lead:", choices)
            if choice is None or choice == back_label:
                return None

            if choice == "previous":
                return {"action": "previous"}
            if choice == "next":
                return {"action": "next"}

            result = self.prompt_call_outcome(lead=lead, remaining=remaining)
            if result is None:
                continue

            return {
                "action": "outcome",
                "outcome": result["outcome"],
                "description": result.get("description", ""),
            }

    def prompt_call_outcome(self, lead=None, remaining=None):
        """
        Prompt for a call outcome and optional description

        Draws the dial lead Panel, then the questionary outcome menu.

        Args:
            lead: Lead dict (phone used by Copy number; card redraw)
            remaining: Optional dialable queue count for the card header

        Returns:
            Dict with 'outcome' and 'description', or None if cancelled/back
        """
        lead = lead or {}
        phone = (lead.get("phone") or "").strip()
        label_to_code = {label: code for label, code in OUTCOME_MENU_CHOICES}
        copy_label = "Copy number"
        choices = [copy_label] + list(label_to_code.keys()) + ["< Back>"]

        while True:
            ansi_clear()
            if lead:
                self.display.display_dial_lead(lead, remaining=remaining)

            choice = self._show_menu("Log call outcome:", choices)
            if choice is None or choice == "< Back>":
                return None

            if choice == copy_label:
                if not phone:
                    print_plain("No phone number to copy.")
                    self._press_any_key()
                    continue
                try:
                    pyperclip.copy(phone)
                except Exception as e:
                    print_plain(f"Could not copy to clipboard: {e}")
                    self._press_any_key()
                    continue

                ansi_clear()
                if lead:
                    self.display.display_dial_lead(lead, remaining=remaining)
                print_plain(f"✓ Copied  {phone}")
                time.sleep(0.75)
                continue

            outcome = label_to_code[choice]

            description = self._text("Description (optional):", default="")
            if description is None:
                return None

            return {
                "outcome": outcome,
                "description": description.strip(),
            }
