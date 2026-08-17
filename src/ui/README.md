### /src/ui
- `interface.py` - Facade class, composes all managers and provides the public API
- `display.py` - Handles Rich console initialization, theming, streaming, dial lead cards, and analytics
- `input.py` - Handles `prompt_toolkit` sessions, input capture, and keyboard shortcuts
- `menus.py` - Handles interactive `questionary` menus (ANSI clear + plain text before selects)
- `terminal.py` - ANSI clear, cursor helpers, plain print for menu handoffs
