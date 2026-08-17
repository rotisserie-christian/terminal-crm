import sys
import shutil
import time
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
import src.config as config
from src.storage import LEAD_STATUSES, OUTCOME_MENU_CHOICES, ratio_bar


class DisplayManager:
    """Manages all display output using Rich console"""
    
    def __init__(self):
        # Rich console with custom theme
        custom_theme = Theme({
            "info": "dim cyan",
            "user": config.PRIMARY_COLOR,
            "assistant": config.SECONDARY_COLOR,
            "warning": "magenta",
            "danger": "bold red"
        })
        self.console = Console(theme=custom_theme)
    
    def display_welcome(self):
        """Welcome box, displays title and portfolio link"""
        self.console.print(
            Panel.fit(
                f"[bold {config.SECONDARY_COLOR}]Terminal CRM[/bold {config.SECONDARY_COLOR}]\n"
                f"[dim]christianwaters.dev[/dim]",
                border_style=config.SECONDARY_COLOR
            )
        )

    def display_model_stream(self, generator):
        """
        Display streaming response with word wrapping
        
        Buffers tokens until whitespace/punctuation to avoid breaking words
        Manually wraps at terminal width to prevent mid-word breaks
        
        Args:
            generator: Text token generator from model
            
        Returns:
            str: Complete assistant response
        """
        terminal_width = shutil.get_terminal_size().columns
        safe_width = terminal_width - 3
        
        # Print prefix
        prefix = f"\n[bold {config.SECONDARY_COLOR}]{config.MODEL_DISPLAY_NAME} >[/bold {config.SECONDARY_COLOR}] "
        self.console.print(prefix, end="")
        
        current_text = ""
        buffer = ""
        current_line_length = len(f"{config.MODEL_DISPLAY_NAME} > ")
        
        for token in generator:
            current_text += token
            buffer += token
            
            # Flush on whitespace/punctuation or when buffer gets long
            should_flush = (
                any(char in token for char in [' ', '\n', '\t', '.', ',', '!', '?', ';', ':']) 
                or len(buffer) > 20
            )
            
            if should_flush:
                # Check if buffer exceeds terminal width
                if current_line_length + len(buffer) > safe_width:
                    sys.stdout.write('\n')
                    current_line_length = 0
                
                sys.stdout.write(buffer)
                sys.stdout.flush()
                
                # Update line length tracker
                if '\n' in buffer:
                    last_newline_pos = buffer.rfind('\n')
                    current_line_length = len(buffer) - last_newline_pos - 1
                else:
                    current_line_length += len(buffer)
                
                buffer = ""
        
        # Flush remaining buffer
        if buffer:
            if current_line_length + len(buffer) > safe_width:
                sys.stdout.write('\n')
            sys.stdout.write(buffer)
            sys.stdout.flush()
        
        self.console.print()
        return current_text

    def display_system_message(self, message):
        """Display a dimmed system message"""
        self.console.print(f"[dim]{message}[/dim]")

    def display_lead_files_pending(self, filenames):
        """
        List lead JSON files that will be merged

        Args:
            filenames: List of filenames in /leads
        """
        self.console.print("\n[bold]Lead files ready to merge[/bold]")
        for name in filenames:
            self.console.print(f"  [info]•[/info] {name}")
        self.console.print()

    def display_lead_import_summary(self, summary):
        """
        Display results from a lead JSON import

        Args:
            summary: Dict with added/updated/skipped/files/loaded/errors
        """
        self.console.print("\n[bold]Lead import complete[/bold]")
        self.console.print(
            f"[info]Files processed:[/info] {summary.get('files', 0)}  "
            f"[info]Loaded:[/info] {summary.get('loaded', 0)}"
        )
        self.console.print(
            f"[info]Added:[/info] {summary.get('added', 0)}  "
            f"[info]Updated:[/info] {summary.get('updated', 0)}  "
            f"[info]Skipped:[/info] {summary.get('skipped', 0)}"
        )

        errors = summary.get("errors") or []
        if not summary.get("files") and not errors:
            self.console.print(
                "[dim]No JSON files found in /leads. "
                "Add a lead list (see leads/sample.json) and try again.[/dim]"
            )

        for err in errors:
            self.console.print(
                f"[warning]Skipped file {err.get('file')}: {err.get('error')}[/warning]"
            )

    def display_dial_lead(self, lead, remaining=None):
        """
        Display a single lead for the dial screen

        Args:
            lead: Lead dict from get_next_dial_lead
            remaining: Optional count of dialable leads still in queue
        """
        company = lead.get("company") or "(no company)"
        phone = lead.get("phone") or "(no phone)"
        status = lead.get("status") or "new"

        def field(value):
            text = "" if value is None else str(value).strip()
            return text if text else "-"

        def flag(value):
            return "yes" if value else "no"

        header = f"[bold {config.SECONDARY_COLOR}]{company}[/bold {config.SECONDARY_COLOR}]"
        if remaining is not None:
            header += f"\n[dim]Queue: {remaining} remaining[/dim]"

        body = "\n".join(
            [
                f"[bold]Phone[/bold]    {phone}",
                f"[bold]Status[/bold]   {status}",
                f"[bold]Trade[/bold]    {field(lead.get('trade'))}",
                f"[bold]Website[/bold]  {field(lead.get('website'))}",
                f"[bold]Signals[/bold]  {field(lead.get('signals'))}",
                f"[bold]Hiring[/bold]   {field(lead.get('hiring'))}",
                f"[bold]Is hiring[/bold]  {flag(lead.get('is_hiring'))}",
                f"[bold]Has ads[/bold]    {flag(lead.get('has_ads'))}",
            ]
        )

        self.console.print()
        self.console.print(
            Panel(
                f"{header}\n\n{body}",
                title="Dial",
                border_style=config.SECONDARY_COLOR,
            )
        )

    def _analytics_table(self, title, rows, total):
        table = Table(
            title=title,
            show_header=True,
            header_style="bold",
            box=None,
            pad_edge=False,
            expand=False,
        )
        table.add_column(" ", style="bold")
        table.add_column("n", justify="right")
        table.add_column("%", justify="right", style="dim")
        table.add_column(" ", no_wrap=True)

        for label, count in rows:
            if total <= 0:
                pct = "0%"
            else:
                pct = f"{round(100 * count / total)}%"
            bar = ratio_bar(count, total)
            table.add_row(label, str(count), pct, f"[dim]{bar}[/dim]")
        return table

    def display_analytics(self, lead_stats, outcome_stats, scope_label="Full list"):
        """
        Display lead and call outcome counts for a filter scope

        Args:
            lead_stats: Dict from lead_status_counts
            outcome_stats: Dict from outcome_counts
            scope_label: Panel subtitle (e.g. 'BC', 'Full list')
        """
        status_labels = {
            "new": "New",
            "callback": "Callback",
            "not_interested": "Not interested",
            "do_not_call": "Do not call",
            "wrong_number": "Wrong number",
            "closed": "Closed / Won",
        }
        outcome_labels = {code: label for label, code in OUTCOME_MENU_CHOICES}

        by_status = lead_stats.get("by_status") or {}
        lead_total = int(lead_stats.get("total") or 0)
        lead_rows = [("In queue", int(lead_stats.get("queue") or 0))]
        for status in LEAD_STATUSES:
            lead_rows.append(
                (status_labels.get(status, status), int(by_status.get(status, 0)))
            )

        by_outcome = outcome_stats.get("by_outcome") or {}
        outcome_total = int(outcome_stats.get("total") or 0)
        outcome_rows = [
            (outcome_labels.get(code, code), int(by_outcome.get(code, 0)))
            for _, code in OUTCOME_MENU_CHOICES
        ]

        body = Group(
            self._analytics_table("Leads", lead_rows, lead_total),
            self._analytics_table("Calls", outcome_rows, outcome_total),
        )

        self.console.print()
        self.console.print(
            Panel(
                body,
                title=f"Analytics — {scope_label}",
                border_style=config.SECONDARY_COLOR,
            )
        )

    def display_copied_flash(self, phone: str, duration: float = 0.75):
        """
        Briefly show a transient "Copied" confirmation

        Args:
            phone: Phone number that was copied
            duration: Seconds to keep the status visible
        """
        message = f"[bold green]✓ Copied[/bold green]  [dim]{phone}[/dim]"
        with Live(
            message,
            console=self.console,
            transient=True,
            refresh_per_second=8,
        ):
            time.sleep(duration)

    def display_error(self, message):
        """Display an error message"""
        self.console.print(f"[danger]Error: {message}[/danger]")

    def clear_screen(self):
        """Clear the terminal screen"""
        self.console.clear()

    def status(self, message: str):
        """
        Rich status spinner context manager for loading feedback

        Args:
            message: Status text to show beside the spinner
        """
        return self.console.status(f"[cyan]{message}[/cyan]", spinner="dots")
