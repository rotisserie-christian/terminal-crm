import questionary


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
        self._menu_style = questionary.Style([
            ('qmark', 'fg:cyan bold'),
            ('question', 'bold'),
            ('answer', 'fg:cyan bold'),
            ('pointer', 'fg:cyan bold'),
            ('highlighted', 'fg:cyan bold'),
            ('selected', 'fg:cyan bold'),
            ('separator', 'fg:#cc5454'),
            ('instruction', 'fg:#909090'),
            ('text', ''),
            ('disabled', 'fg:#858585 italic')
        ])
    
    def _show_menu(self, title, choices):
        """
        Menu display helper
        
        Args:
            title: Menu title string
            choices: List of strings (menu options)
            
        Returns:
            Selected choice string, or None if cancelled
        """
        try:
            choice = questionary.select(
                title,
                choices=choices,
                style=self._menu_style,
                use_arrow_keys=True
            ).ask()
            return choice
        except KeyboardInterrupt:
            return None

    def show_main_menu(self):
        """
        Display the main menu
        
        Returns:
            str: Selected option ('Add Leads', 'New Chat', 'Load Chat',
                 'Settings', or 'Exit')
        """
        self.display.clear_screen()
        self.display.display_welcome()
        
        choice = self._show_menu(
            "Select an option:",
            ["Add Leads", "New Chat", "Load Chat", "Settings", "Exit"]
        )
        return choice if choice else "Exit"

    def show_lead_import_summary(self, summary):
        """
        Display lead import results and wait for acknowledgment

        Args:
            summary: Import summary dict from import_leads_from_directory
        """
        self.display.display_lead_import_summary(summary)
        questionary.press_any_key_to_continue().ask()

    def confirm_lead_import(self, filenames):
        """
        Show pending lead JSON filenames and ask to confirm merge

        Args:
            filenames: List of lead JSON filenames

        Returns:
            True if the user confirms the merge, False otherwise
        """
        if not filenames:
            self.display.display_system_message(
                "No JSON files found in /leads. "
                "Add a lead list (see leads/sample.json) and try again."
            )
            questionary.press_any_key_to_continue().ask()
            return False

        self.display.display_lead_files_pending(filenames)

        try:
            confirmed = questionary.confirm(
                f"Merge {len(filenames)} file(s) into the CRM database?",
                default=True,
                style=self._menu_style,
            ).ask()
        except KeyboardInterrupt:
            return False

        return bool(confirmed)

    def show_chat_selection(self, chats):
        """
        Display chat selection menu
        
        Args:
            chats: List of chat filenames
            
        Returns:
            str: Selected chat filename, or None if cancelled/no chats
        """
        if not chats:
            self.display.display_error("No saved chats found.")
            questionary.press_any_key_to_continue().ask()
            return None
        
        choices = chats + ["< Back"]
        choice = self._show_menu("Select a chat to load:", choices)
        
        if choice == "< Back" or choice is None:
            return None
        return choice
