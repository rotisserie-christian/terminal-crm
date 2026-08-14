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


class RAGSettingsMenu:
    """Handles the RAG settings submenu."""

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
        Display and handle the RAG settings submenu.

        Args:
            style: Menu styling object
        """
        while True:
            ansi_clear()
            self._show_summary()

            choice = self._select(
                "RAG Settings",
                [
                    "Enable/Disable RAG",
                    "Context Percentage",
                    "Top-K Retrieval",
                    "Relevance Cutoff",
                    "Back",
                ],
                style,
            )

            if choice is None:
                sys.exit(0)

            if choice == "Back":
                break

            elif choice == "Enable/Disable RAG":
                self._toggle_rag(style)

            elif choice == "Context Percentage":
                sync_after_rich(self.console)
                show_cursor()
                new_percentage = get_float_input(
                    self.console,
                    "RAG Context Percentage (0.10 = 10%, 0.50 = 50%)",
                    config.RAG_CONTEXT_PERCENTAGE,
                    0.05,
                    0.50,
                )
                if new_percentage is not None:
                    config.RAG_CONTEXT_PERCENTAGE = new_percentage

            elif choice == "Top-K Retrieval":
                sync_after_rich(self.console)
                show_cursor()
                new_top_k = get_int_input(
                    self.console,
                    "Top-K (number of chunks to consider)",
                    config.RAG_TOP_K,
                    1,
                    50,
                )
                if new_top_k is not None:
                    config.RAG_TOP_K = new_top_k

            elif choice == "Relevance Cutoff":
                sync_after_rich(self.console)
                show_cursor()
                new_cutoff = get_float_input(
                    self.console,
                    "Relevance cutoff (0.0-1.0 cosine; skip RAG if nothing is this similar)",
                    config.RAG_RELEVANCE_CUTOFF,
                    0.0,
                    1.0,
                )
                if new_cutoff is not None:
                    config.RAG_RELEVANCE_CUTOFF = new_cutoff

    def _toggle_rag(self, style):
        """Handle RAG enable/disable toggle."""
        ansi_clear()
        current_state = "enabled" if config.RAG_ENABLED else "disabled"
        sync_after_rich(self.console)
        show_cursor()
        toggle_result = questionary.confirm(
            f"RAG is currently {current_state}. Enable RAG?",
            default=config.RAG_ENABLED,
            style=style,
        ).ask()

        if toggle_result is None:
            sys.exit(0)

        config.RAG_ENABLED = toggle_result

    def _show_summary(self):
        """Display current RAG settings as plain text."""
        rag_status = "Enabled" if config.RAG_ENABLED else "Disabled"
        percentage_display = f"{int(config.RAG_CONTEXT_PERCENTAGE * 100)}%"

        print_plain("RAG Settings")
        print_plain("")
        print_plain(f"Status: {rag_status}")
        print_plain(f"Context Percentage: {percentage_display}")
        print_plain(f"Top-K Retrieval: {config.RAG_TOP_K}")
        print_plain(f"Relevance Cutoff: {config.RAG_RELEVANCE_CUTOFF}")
        print_plain("")
        print_plain(
            "RAG uses files from the /memory directory to provide "
            "context-aware responses based on your knowledge base."
        )
        print_plain(
            "Chunks below the relevance cutoff are ignored. If nothing "
            "is similar enough, RAG is skipped for that message."
        )
        print_plain("")
