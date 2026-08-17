import questionary
import pyperclip

from src.storage.crm_outcomes import OUTCOME_MENU_CHOICES
from .terminal import (
    ansi_clear,
    hidden_cursor,
    print_plain,
    show_cursor,
    sync_after_rich,
)


class MenuManager:
    """Manages interactive menus"""

    def __init__(self, display_manager):
        """
        Initialize menu manager

        Args:
            display_manager: DisplayManager instance for screen operations
        """
        self.display = display_manager

        # Questionary menu style (used by all menus)
        self._menu_style = questionary.Style(
            [
                ("qmark", "fg:cyan bold"),
                ("question", "bold"),
                ("answer", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
                ("selected", "fg:cyan bold"),
                ("separator", "fg:#cc5454"),
                ("instruction", "fg:#909090"),
                ("text", ""),
                ("disabled", "fg:#858585 italic"),
            ]
        )

    def _handoff_to_prompt(self) -> None:
        """Flush stdout before opening a questionary prompt."""
        sync_after_rich(getattr(self.display, "console", None))

    def _show_menu(self, title, choices):
        """
        Menu display helper (no Rich immediately before this).

        Args:
            title: Menu title string
            choices: List of strings or questionary.Choice values

        Returns:
            Selected choice (string or Choice value), or None if cancelled
        """
        self._handoff_to_prompt()
        try:
            with hidden_cursor():
                choice = questionary.select(
                    title,
                    choices=choices,
                    style=self._menu_style,
                    use_arrow_keys=True,
                ).ask()
            return choice
        except KeyboardInterrupt:
            return None
        finally:
            show_cursor()

    def _confirm(self, message: str, default: bool = True):
        """Confirm prompt with visible cursor."""
        self._handoff_to_prompt()
        show_cursor()
        try:
            return questionary.confirm(
                message,
                default=default,
                style=self._menu_style,
            ).ask()
        except KeyboardInterrupt:
            return None

    def _text(self, message: str, default: str = ""):
        """Text prompt with visible cursor."""
        self._handoff_to_prompt()
        show_cursor()
        try:
            return questionary.text(
                message,
                default=default,
                style=self._menu_style,
            ).ask()
        except KeyboardInterrupt:
            return None

    def _press_any_key(self) -> None:
        """Wait for a key."""
        self._handoff_to_prompt()
        show_cursor()
        questionary.press_any_key_to_continue().ask()

    def show_main_menu(self):
        """
        Display the main menu

        Returns:
            str: Selected option ('Add Leads', 'Dial', 'New Chat', 'Load Chat',
                 'Settings', or 'Exit')
        """
        # ANSI clear only — no Rich panel before questionary (avoids stray cursor)
        ansi_clear()
        choice = self._show_menu(
            "Terminal CRM — Select an option:",
            ["Add Leads", "Dial", "New Chat", "Load Chat", "Settings", "Exit"],
        )
        return choice if choice else "Exit"

    def show_lead_import_summary(self, summary):
        """
        Display lead import results and wait for acknowledgment

        Args:
            summary: Import summary dict from import_leads_from_directory
        """
        ansi_clear()
        print_plain("Lead import complete")
        print_plain(
            f"Files processed: {summary.get('files', 0)}  "
            f"Loaded: {summary.get('loaded', 0)}"
        )
        print_plain(
            f"Added: {summary.get('added', 0)}  "
            f"Updated: {summary.get('updated', 0)}  "
            f"Skipped: {summary.get('skipped', 0)}"
        )
        errors = summary.get("errors") or []
        if not summary.get("files") and not errors:
            print_plain(
                "No JSON files found in /leads. "
                "Add a lead list (see leads/sample.json) and try again."
            )
        for err in errors:
            print_plain(f"Skipped file {err.get('file')}: {err.get('error')}")
        print_plain("")
        self._press_any_key()

    def confirm_lead_import(self, filenames):
        """
        Show pending lead JSON filenames and ask to confirm merge

        Args:
            filenames: List of lead JSON filenames

        Returns:
            True if the user confirms the merge, False otherwise
        """
        ansi_clear()
        if not filenames:
            print_plain(
                "No JSON files found in /leads. "
                "Add a lead list (see leads/sample.json) and try again."
            )
            print_plain("")
            self._press_any_key()
            return False

        print_plain("Lead files ready to merge")
        for name in filenames:
            print_plain(f"  - {name}")
        print_plain("")

        confirmed = self._confirm(
            f"Merge {len(filenames)} file(s) into the CRM database?",
            default=True,
        )
        return bool(confirmed)

    def prompt_dial_filter(self):
        """
        Prompt for dial queue scope before starting the dial loop

        Returns:
            Dict with 'region' ('bc', 'on', or None for full list),
            or None if cancelled/back
        """
        location_labels = {
            "British Columbia": "bc",
            "Ontario": "on",
        }

        while True:
            ansi_clear()
            scope = self._show_menu(
                "Dial filter:",
                ["Full list", "Location", "< Back>"],
            )
            if scope is None or scope == "< Back>":
                return None

            if scope == "Full list":
                return {"region": None}

            while True:
                ansi_clear()
                place = self._show_menu(
                    "Location:",
                    list(location_labels.keys()) + ["< Back>"],
                )
                if place is None or place == "< Back>":
                    break
                return {"region": location_labels[place]}

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
                import time

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

    def show_chat_selection(self, chats):
        """
        Display chat selection menu

        Args:
            chats: List of chat filenames

        Returns:
            str: Selected chat filename, or None if cancelled/no chats
        """
        ansi_clear()
        if not chats:
            print_plain("No saved chats found.")
            print_plain("")
            self._press_any_key()
            return None

        choices = chats + ["< Back"]
        choice = self._show_menu("Select a chat to load:", choices)

        if choice == "< Back" or choice is None:
            return None
        return choice
