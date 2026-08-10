# Terminal CRM

Terminal-based CRM with a dial queue and optional local LLM chat

> [!NOTE]  
> This is not an auto-dialer or a spam script. It's for working small lead lists and brainstorming in the privacy of your own hardware. 

## Table of Contents

- [Getting Started](#getting-started)
- [Adding Leads](#adding-leads)
- [Tracking Leads](#tracking-leads)
- [Brainstorming](#brainstorming)

## Getting Started

Python 3.10+.

```bash
git clone https://github.com/rotisserie-christian/terminal-crm
cd terminal-crm
pip install -r requirements.txt
```

CLI (optional)

```bash
pip install -e .
```

Run:

```bash
python main.py
# or
terminal-crm
```

Menus use arrow keys and Enter. Exit with `ctrl + c`, or choose Exit from the main menu.

Settings live in `config.json` (edit the file or use **Settings** in the app).

## Adding Leads

1. Put lead JSON files in `/leads`.
2. Choose **Add Leads** from the main menu to merge them into the local SQLite CRM (`data/`).

Each lead needs at least a usable `phone`. Import skips invalid or empty numbers and updates existing leads matched by phone.

## Tracking Leads

Choose **Dial** to work the queue.

Filter first:

- **Full list**: all dialable leads (`new` or `callback`)
- **Location**: British Columbia or Ontario only (by phone area code; toll-free excluded)

Per call you can:

- **Copy number**: clipboard only, does not log an outcome
- **Voicemail** / **No answer**: stay in queue as `new`
- **Callback**: stay in queue, prioritized next
- **Not interested** / **Wrong number** / **Closed / Won**: leave the dial queue

## Brainstorming

- **New Chat**: start a local LLM conversation
- **Load Chat**: resume a session from `/chats`

RAG is off by default. Enable it in **Settings**, then add `.md` / `.txt` files under `/memory` for retrieved context.
