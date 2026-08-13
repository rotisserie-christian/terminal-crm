# Terminal CRM

Terminal-based CRM with a dial queue and optional local LLM chat

> [!NOTE]  
> This is not an auto-dialer or a spam script. It's for manually working small lists and brainstorming in the privacy of your own hardware. 

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

Each lead needs at least a usable `phone`. Import skips invalid or empty numbers and updates existing leads matched by phone. `status`, `created_at`, and `updated_at` are set by the CRM (new imports start as `new`).

### Lead list JSON

A file may be a top-level array, or an object with a `leads` array:

```json
[
  {
    "company": "Serious Business Inc.",
    "website": "https://serious.biz",
    "trade": "roofing",
    "signals": "No tap-to-call in hero; long contact form",
    "hiring": "",
    "phone": "+1 604-123-1234",
    "is_hiring": false,
    "has_ads": true
  }
]
```

```json
{ "leads": [ { "company": "Serious Business Inc.", "phone": "3061231234" } ] }
```

| Field | Required | Notes |
| --- | --- | --- |
| `phone` | yes | Any format; stored as digits only. Duplicate phones update the existing row. |
| `company` | no | Display name |
| `website` | no | URL |
| `trade` | no | What industry/type of business they do |
| `signals` | no | Whatever indicates they might be interested |
| `hiring` | no | Notes on what they're hiring for, if they're hiring |
| `is_hiring` | no | Boolean: `true`/`false`, `1`/`0`, `yes`/`no` (default `0`) |
| `has_ads` | no | Boolean |

## Tracking Leads

Choose **Dial** to work the queue.

Filter first:

- **Full list**: all dialable leads (`new` or `callback`)
- **Location**: By phone area code, toll-free numbers are excluded since they are crap 99/100 times

Per call you can:

- **Copy number**: clipboard only, does not log an outcome
- **Voicemail** / **No answer**: stay in queue as `new`
- **Callback**: stay in queue, prioritized next
- **Not interested** / **Wrong number** / **Closed / Won**: leave the dial queue

## Brainstorming

- **New Chat**: start a local LLM conversation
- **Load Chat**: resume a session from `/chats`

Pick a Hugging Face model ID in **Settings** (default list or enter manually), or set `model_name` in `config.json`.

RAG is off by default. Enable it in **Settings**, then add `.md` / `.txt` files under `/memory` for retrieved context.
