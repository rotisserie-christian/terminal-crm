from .display import DisplayManager
from .input import InputManager
from .menus import MenuManager


class TerminalUI:
    """
    Handles all terminal UI interactions including menus, input, and output display
    
    Manages:
    - Rich console for formatted output
    - Prompt_toolkit for input
    - Questionary for interactive menus
    """
    
    def __init__(self):
        self._display = DisplayManager()
        self._input = InputManager()
        self._menus = MenuManager(self._display)
    
    # Expose console for backward compatibility
    @property
    def console(self):
        """Access to the Rich console instance"""
        return self._display.console
    
    # Display methods
    def display_welcome(self):
        """Welcome box, displays title and portfolio link"""
        self._display.display_welcome()
    
    def display_model_stream(self, generator):
        """
        Display streaming response with word wrapping
        
        Args:
            generator: Text token generator from model
            
        Returns:
            str: Complete assistant response
        """
        return self._display.display_model_stream(generator)
    
    def display_system_message(self, message):
        """Display a dimmed system message"""
        self._display.display_system_message(message)
    
    def display_error(self, message):
        """Display an error message"""
        self._display.display_error(message)

    def display_dial_lead(self, lead, remaining=None):
        """
        Display a single lead for the dial screen

        Args:
            lead: Lead dict from get_next_dial_lead
            remaining: Optional count of dialable leads still in queue
        """
        self._display.display_dial_lead(lead, remaining=remaining)

    def display_analytics(self, lead_stats, outcome_stats, scope_label="Full list"):
        """
        Display lead and call outcome counts for a filter scope

        Args:
            lead_stats: Dict from lead_status_counts
            outcome_stats: Dict from outcome_counts
            scope_label: Panel subtitle (e.g. 'BC', 'Full list')
        """
        self._display.display_analytics(
            lead_stats,
            outcome_stats,
            scope_label=scope_label,
        )
    
    def clear_screen(self):
        """Clear the terminal screen"""
        self._display.clear_screen()

    def status(self, message: str):
        """
        Rich status spinner context manager for loading feedback

        Args:
            message: Status text to show beside the spinner
        """
        return self._display.status(message)
    
    # Input methods
    def get_input(self):
        """
        Get user input with keyboard shortcuts
        
        Returns:
            str: User input, or special signals 'RETURN_TO_MENU'/'MANUAL_SAVE', 
                 or None on exit
        """
        return self._input.get_input()
    
    # Menu methods
    def show_main_menu(self):
        """
        Display the main menu
        
        Returns:
            str: Selected option ('Add Leads', 'Dial', 'New Chat', 'Load Chat',
                 'Settings', or 'Exit')
        """
        return self._menus.show_main_menu()

    def show_lead_import_summary(self, summary):
        """
        Display lead import results and wait for acknowledgment

        Args:
            summary: Import summary dict from import_leads_from_directory
        """
        return self._menus.show_lead_import_summary(summary)

    def show_analytics(self, lead_stats, outcome_stats, scope_label="Full list"):
        """
        Display analytics and wait for acknowledgment

        Args:
            lead_stats: Dict from lead_status_counts
            outcome_stats: Dict from outcome_counts
            scope_label: Panel subtitle (e.g. 'BC', 'Full list')
        """
        return self._menus.show_analytics(
            lead_stats,
            outcome_stats,
            scope_label=scope_label,
        )

    def confirm_lead_import(self, filenames):
        """
        Show pending lead JSON filenames and ask to confirm merge

        Args:
            filenames: List of lead JSON filenames

        Returns:
            True if the user confirms the merge, False otherwise
        """
        return self._menus.confirm_lead_import(filenames)

    def prompt_list_filter(self):
        """
        Prompt for Full list vs location before Dial or Analytics

        Returns:
            Dict with 'region' ('bc', 'on', or None for full list),
            or None if cancelled/back
        """
        return self._menus.prompt_list_filter()

    def prompt_dial_actions(
        self,
        lead=None,
        remaining=None,
        can_previous=False,
        can_next=False,
    ):
        """
        Prompt to browse the dial queue or edit the current lead

        Args:
            lead: Lead dict for the card and nested outcome menu
            remaining: Optional dialable queue count for the card header
            can_previous: When False, Previous is disabled
            can_next: When False, Next is disabled

        Returns:
            Dict with 'action' of 'previous', 'next', or 'outcome',
            or None if cancelled/back
        """
        return self._menus.prompt_dial_actions(
            lead=lead,
            remaining=remaining,
            can_previous=can_previous,
            can_next=can_next,
        )

    def prompt_call_outcome(self, lead=None, remaining=None):
        """
        Prompt for a call outcome and optional description

        Args:
            lead: Lead dict (phone used by Copy number; card redraw)
            remaining: Optional dialable queue count for the card header

        Returns:
            Dict with 'outcome' and 'description', or None if cancelled/back
        """
        return self._menus.prompt_call_outcome(lead=lead, remaining=remaining)
    
    def show_chat_selection(self, chats):
        """
        Display chat selection menu
        
        Args:
            chats: List of chat filenames
            
        Returns:
            str: Selected chat filename, or None if cancelled/no chats
        """
        return self._menus.show_chat_selection(chats)

