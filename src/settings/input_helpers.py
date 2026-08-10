import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style as PtStyle
import src.config as config
from src.ui.terminal import show_cursor, sync_after_rich


def get_text_input(console, label: str, default: str) -> str | None:
    """
    Get text input with Esc key support
    
    Args:
        console: Rich Console instance for output
        label: Label to display
        default: Default/current value
        
    Returns:
        str: User input, or None if cancelled
    """
    bindings = KeyBindings()

    @bindings.add(Keys.Escape)
    def _(event):
        event.app.exit(result=None)

    style = PtStyle.from_dict({
        'prompt': f'ansi{config.PRIMARY_COLOR} bold',
    })
    
    session = PromptSession(key_bindings=bindings, style=style)
    
    try:
        console.print(f"\n[yellow]{label}[/yellow]")
        console.print(f"[dim]Current: {default} (Press Esc to go back)[/dim]")
        sync_after_rich(console)
        show_cursor()
        
        result = session.prompt(f"> ", default=default)
        return result
    except KeyboardInterrupt:
        sys.exit(0)


def get_float_input(console, label: str, current: float, min_val: float, max_val: float) -> float | None:
    """
    Get validated float input within a range
    
    Args:
        console: Rich Console instance for output
        label: Parameter name to display
        current: Current value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        float: Valid input value, or None if cancelled
    """

    bindings = KeyBindings()

    @bindings.add(Keys.Escape)
    def _(event):
        event.app.exit(result=None)

    style = PtStyle.from_dict({
        'prompt': f'ansi{config.PRIMARY_COLOR} bold',
    })
    
    session = PromptSession(key_bindings=bindings, style=style)
    
    while True:
        try:
            console.print(f"\n[yellow]{label}[/yellow]")
            console.print(f"[dim]Current: {current} | Range: {min_val}-{max_val} (Press Esc to go back)[/dim]")
            sync_after_rich(console)
            show_cursor()
            
            result = session.prompt(f"> ", default=str(current))
            
            if result is None:
                return None
            
            try:
                value = float(result)
                
                if value < min_val or value > max_val:
                    console.print(f"[red]Value must be between {min_val} and {max_val}[/red]")
                    continue
                
                return value
                
            except ValueError:
                console.print(f"[red]Invalid number. Please enter a value between {min_val} and {max_val}[/red]")
                continue
                
        except KeyboardInterrupt:
            sys.exit(0)


def get_int_input(console, label: str, current: int, min_val: int, max_val: int) -> int | None:
    """
    Get validated integer input within a range
    
    Args:
        console: Rich Console instance for output
        label: Parameter name to display
        current: Current value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        int: Valid input value, or None if cancelled
    """

    bindings = KeyBindings()

    @bindings.add(Keys.Escape)
    def _(event):
        event.app.exit(result=None)

    style = PtStyle.from_dict({
        'prompt': f'ansi{config.PRIMARY_COLOR} bold',
    })
    
    session = PromptSession(key_bindings=bindings, style=style)
    
    while True:
        try:
            console.print(f"\n[yellow]{label}[/yellow]")
            console.print(f"[dim]Current: {current} | Range: {min_val}-{max_val} (Press Esc to go back)[/dim]")
            sync_after_rich(console)
            show_cursor()
            
            result = session.prompt(f"> ", default=str(current))
            
            if result is None:
                return None
            
            try:
                value = int(result)
                
                if value < min_val or value > max_val:
                    console.print(f"[red]Value must be between {min_val} and {max_val}[/red]")
                    continue
                
                return value
                
            except ValueError:
                console.print(f"[red]Invalid number. Please enter an integer between {min_val} and {max_val}[/red]")
                continue
                
        except KeyboardInterrupt:
            sys.exit(0)