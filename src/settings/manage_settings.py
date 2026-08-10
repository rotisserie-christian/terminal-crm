import sys
import questionary
import src.config as config
from .input_helpers import get_text_input
from .model_parameters_menu import ModelParametersMenu
from .rag_settings_menu import RAGSettingsMenu
from src.ui.terminal import (
    ansi_clear,
    hidden_cursor,
    print_plain,
    show_cursor,
    sync_after_rich,
)


class ManageSettings:
    """
    Main settings configuration interface

    Allows user to manage:
    - Model (select from list/enter manually)
    - User Display Name
    - Model Display Name
    - Model Parameters (submenu)
    - RAG Settings (submenu)
    - Autosave Chat

    Settings are persisted to config.json
    """

    def __init__(self, console):
        self.console = console
        self.params_menu = ModelParametersMenu(console)
        self.rag_menu = RAGSettingsMenu(console)
        config.load_config()

    def _select(self, title, choices, style):
        """questionary select with no Rich immediately beforehand."""
        sync_after_rich(self.console)
        try:
            with hidden_cursor():
                return questionary.select(
                    title,
                    choices=choices,
                    style=style,
                    use_arrow_keys=True,
                ).ask()
        finally:
            show_cursor()

    def _confirm(self, message, default, style):
        """questionary confirm."""
        sync_after_rich(self.console)
        show_cursor()
        return questionary.confirm(
            message,
            default=default,
            style=style,
        ).ask()

    def run(self):
        """Run the settings menu loop"""

        style = questionary.Style(
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

        while True:
            ansi_clear()
            self._show_summary()

            choice = self._select(
                "Settings Menu",
                [
                    "Model",
                    "User Display Name",
                    "Model Display Name",
                    "Model Parameters",
                    "RAG Settings",
                    "Autosave Chat",
                    "Back",
                ],
                style,
            )

            if choice is None:
                sys.exit(0)

            if choice == "Back":
                break

            elif choice == "Model":
                self._configure_model(style)

            elif choice == "User Display Name":
                sync_after_rich(self.console)
                show_cursor()
                new_name = get_text_input(
                    self.console, "User Display Name", config.USER_DISPLAY_NAME
                )
                if new_name and new_name.strip():
                    config.USER_DISPLAY_NAME = new_name.strip()

            elif choice == "Model Display Name":
                sync_after_rich(self.console)
                show_cursor()
                new_name = get_text_input(
                    self.console, "Model Display Name", config.MODEL_DISPLAY_NAME
                )
                if new_name and new_name.strip():
                    config.MODEL_DISPLAY_NAME = new_name.strip()

            elif choice == "Model Parameters":
                self.params_menu.show(style)

            elif choice == "RAG Settings":
                self.rag_menu.show(style)

            elif choice == "Autosave Chat":
                self._configure_autosave(style)

        # Save configuration
        if config.save_config():
            print_plain(f"Configuration saved to {config.CONFIG_FILE}")
        else:
            print_plain("Failed to save configuration")

    def _configure_model(self, style):
        """Handle model selection submenu"""

        ansi_clear()
        model_choice = self._select(
            "Model Selection",
            [
                "Select from popular models",
                "Enter manually",
                "Back",
            ],
            style,
        )

        if model_choice is None:
            sys.exit(0)

        if model_choice == "Select from popular models":
            ansi_clear()
            selected_model = self._select(
                "Select Model",
                [
                    "openai-community/gpt2-medium",
                    "openai-community/gpt2-large",
                    "google/gemma-2b-it",
                    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                    "HuggingFaceTB/SmolLM-135M-Instruct",
                    "Back",
                ],
                style,
            )

            if selected_model is None:
                sys.exit(0)

            if selected_model != "Back":
                config.MODEL_NAME = selected_model

        elif model_choice == "Enter manually":
            sync_after_rich(self.console)
            show_cursor()
            new_model = get_text_input(self.console, "Model", config.MODEL_NAME)
            if new_model and new_model.strip():
                config.MODEL_NAME = new_model.strip()

    def _configure_autosave(self, style):
        """Handle autosave toggle"""

        ansi_clear()
        current_state = "enabled" if config.AUTOSAVE_ENABLED else "disabled"
        toggle_result = self._confirm(
            f"Autosave is currently {current_state}. Enable autosave?",
            default=config.AUTOSAVE_ENABLED,
            style=style,
        )

        if toggle_result is None:
            sys.exit(0)

        config.AUTOSAVE_ENABLED = toggle_result

    def _show_summary(self):
        """Display current configuration summary as plain text."""
        autosave_status = "Enabled" if config.AUTOSAVE_ENABLED else "Disabled"
        rag_status = "Enabled" if config.RAG_ENABLED else "Disabled"

        print_plain("Current Configuration")
        print_plain("")
        print_plain(f"Model: {config.MODEL_NAME}")
        print_plain(f"User Display: {config.USER_DISPLAY_NAME}")
        print_plain(f"Model Display: {config.MODEL_DISPLAY_NAME}")
        print_plain(f"Primary Color: {config.PRIMARY_COLOR}")
        print_plain(f"Secondary Color: {config.SECONDARY_COLOR}")
        print_plain(f"Autosave: {autosave_status}")
        print_plain(f"RAG: {rag_status}")
        print_plain("")
