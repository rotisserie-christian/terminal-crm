from src.storage import CrmDatabase, lead_status_counts, outcome_counts
from src.ui import TerminalUI


_SCOPE_LABELS = {
    "bc": "BC",
    "on": "Ontario",
}


class AnalyticsScreen:
    """
    Show lead and call counts for a Full list or location filter

    Empty databases still show the zero table.
    """

    def __init__(self, ui: TerminalUI, crm_db: CrmDatabase):
        """
        Initialize analytics screen

        Args:
            ui: Terminal UI instance
            crm_db: CRM database instance
        """
        self.ui = ui
        self.crm_db = crm_db

    def run(self) -> None:
        """Prompt for scope, load counts, and display the analytics panel."""
        filter_choice = self.ui.prompt_list_filter()
        if filter_choice is None:
            self.ui.display_system_message("Returning to menu...")
            return

        region = filter_choice.get("region")
        if region:
            scope_label = _SCOPE_LABELS.get(region, region)
        else:
            scope_label = "Full list"

        with self.ui.status("Loading analytics..."):
            lead_stats = lead_status_counts(self.crm_db, region=region)
            outcome_stats = outcome_counts(self.crm_db, region=region)

        self.ui.show_analytics(
            lead_stats,
            outcome_stats,
            scope_label=scope_label,
        )
