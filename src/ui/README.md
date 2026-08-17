### /src/ui
- `interface.py` - Facade class, composes all managers and provides the public API
- `display.py` - Handles Rich console initialization, theming, streaming, dial lead cards, and analytics
- `input.py` - Handles `prompt_toolkit` sessions, input capture, and keyboard shortcuts
- `menus.py` - Questionary menus (main, import, filter, analytics, chat)
- `dial_menus.py` - Dial browse and call-outcome prompts
- `terminal.py` - ANSI clear, cursor helpers, plain print for menu handoffs
