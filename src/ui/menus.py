import questionary

from .dial_menus import DialMenuMixin
from .terminal import (
    ansi_clear,
    hidden_cursor,
    print_plain,
    show_cursor,
    sync_after_rich,
)


class MenuManager(DialMenuMixin):
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
            str: Selected option ('Add Leads', 'Dial', 'Analytics', 'New Chat',
                 'Load Chat', 'Settings', or 'Exit')
        """
        # ANSI clear only — no Rich panel before questionary (avoids stray cursor)
        ansi_clear()
        choice = self._show_menu(
            "Terminal CRM — Select an option:",
            [
                "Add Leads",
                "Dial",
                "Analytics",
                "New Chat",
                "Load Chat",
                "Settings",
                "Exit",
            ],
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

    def show_analytics(self, lead_stats, outcome_stats, scope_label="Full list"):
        """
        Display analytics and wait for acknowledgment

        Args:
            lead_stats: Dict from lead_status_counts
            outcome_stats: Dict from outcome_counts
            scope_label: Panel subtitle (e.g. 'BC', 'Full list')
        """
        ansi_clear()
        self.display.display_analytics(
            lead_stats,
            outcome_stats,
            scope_label=scope_label,
        )
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

    def prompt_list_filter(self):
        """
        Prompt for Full list vs location before Dial or Analytics

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
                "Filter:",
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
