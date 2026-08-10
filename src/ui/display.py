import sys
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
import src.config as config


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
                f"[bold {config.SECONDARY_COLOR}]Terminal Chat[/bold {config.SECONDARY_COLOR}]\n"
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

    def display_error(self, message):
        """Display an error message"""
        self.console.print(f"[danger]Error: {message}[/danger]")

    def clear_screen(self):
        """Clear the terminal screen"""
        self.console.clear()
