import sys
import questionary
import src.config as config
from .input_helpers import get_float_input, get_int_input
from src.ui.terminal import (
    ansi_clear,
    hidden_cursor,
    print_plain,
    show_cursor,
    sync_after_rich,
)


class ModelParametersMenu:
    """Handles the model parameters submenu."""

    def __init__(self, console):
        self.console = console

    def _select(self, title, choices, style):
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

    def show(self, style):
        """
        Display and handle the model parameters submenu.

        Args:
            style: Menu styling object
        """
        while True:
            ansi_clear()
            self._show_summary()

            choice = self._select(
                "Model Parameters",
                [
                    "Temperature",
                    "Top-k",
                    "Top-p",
                    "Max New Tokens",
                    "Back",
                ],
                style,
            )

            if choice is None:
                sys.exit(0)

            if choice == "Back":
                break

            elif choice == "Temperature":
                sync_after_rich(self.console)
                show_cursor()
                new_temp = get_float_input(
                    self.console, "Temperature", config.TEMPERATURE, 0.0, 2.0
                )
                if new_temp is not None:
                    config.TEMPERATURE = new_temp

            elif choice == "Top-k":
                sync_after_rich(self.console)
                show_cursor()
                new_top_k = get_int_input(self.console, "Top-k", config.TOP_K, 1, 100)
                if new_top_k is not None:
                    config.TOP_K = new_top_k

            elif choice == "Top-p":
                sync_after_rich(self.console)
                show_cursor()
                new_top_p = get_float_input(
                    self.console, "Top-p", config.TOP_P, 0.0, 1.0
                )
                if new_top_p is not None:
                    config.TOP_P = new_top_p

            elif choice == "Max New Tokens":
                sync_after_rich(self.console)
                show_cursor()
                new_max_tokens = get_int_input(
                    self.console, "Max New Tokens", config.MAX_NEW_TOKENS, 1, 4096
                )
                if new_max_tokens is not None:
                    config.MAX_NEW_TOKENS = new_max_tokens

    def _show_summary(self):
        """Display current model parameters as plain text."""
        print_plain("Model Parameters")
        print_plain("")
        print_plain(f"Temperature: {config.TEMPERATURE}")
        print_plain(f"Top-k: {config.TOP_K}")
        print_plain(f"Top-p: {config.TOP_P}")
        print_plain(f"Max New Tokens: {config.MAX_NEW_TOKENS}")
        print_plain("")
