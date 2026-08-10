# Terminal Chat

A terminal-based chat interface for local language models. It has rag and save/load features, disabled by default.

## Installation

Clone the repo:
```bash
git clone https://github.com/rotisserie-christian/terminalchat
```


Install dependencies (Python 3.10+):
```bash
pip install -r requirements.txt
```


Install CLI:
```bash
pip install -e .
```


## Usage

Run the main script:

```bash
python main.py
```


Run with CLI:
```bash
terminalchat 
```


### Main Menu
- **Add Leads**: Import JSON lead lists from `/leads` into the local CRM database
- **Dial**: Work the dial queue one lead at a time and log call outcomes
- **New Chat**: Start a fresh conversation
- **Load Chat**: Browse and resume a previously saved session
- **Settings**: Configure the model (HuggingFace ID), display names, and interface colors
- **Exit**: Close the application

### Dial outcomes
When logging a call, choose one of:
- **Copy number** — copy the lead phone to the clipboard (does not log an outcome)
- **Voicemail** / **No answer** — stay in queue (`new`)
- **Callback** — prioritized in the dial queue
- **Not interested** / **Wrong number** / **Closed / Won** — removed from the dial queue

### Controls
- **Arrow Keys**: Navigate menus
- **Enter**: Select an option or send a message
- **Exit/Quit**: `ctrl + c` or `exit` in the main menu

## Configuration

Settings are stored in `config.json`. You can modify this file directly or use the "Settings" menu option within the application.

## Project Structure

- **`main.py`** - Entry point
- **`src/`** - See `src/README.md`
- **`src/app/`** - See `src/app/README.md`
- **`src/rag/`** - See `src/rag/README.md`
- **`src/settings/`** - See `src/settings/README.md`
- **`src/ui/`** - See `src/ui/README.md`
- **`memory/`** - Add files here for RAG (see `memory/README.md`)
- **`chats/`** - Where chat history is saved (JSON format)
- **`leads/`** - Drop lead JSON files here for CRM import (see `leads/README.md`)
- **`data/`** - Local CRM SQLite database (created at runtime)
- **`prompts/`** - System prompts
- **`tests/`** - See `tests/README.md`
- **`config.json`** - Configuration file
