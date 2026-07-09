# GrowEasy CRM CSV Importer

An AI-powered CSV importer that accepts lead data in **any CSV layout** (Facebook Lead
Ads exports, Google Ads exports, Excel sheets, real-estate CRM exports, manual
spreadsheets, etc.) and uses Claude (Anthropic's LLM) to intelligently map the columns
into GrowEasy's fixed CRM schema.

Built for the *Software Developer (Intern / Full-Time) Assignment* at GrowEasy.

## How it works

1. **Upload** — user drags/drops or picks any `.csv` file in the browser.
2. **Preview** — the file is parsed client-side (no AI call yet) and shown in a
   scrollable, sticky-header table so the user can sanity-check it.
3. **Confirm** — user clicks a button, which uploads the actual file to the backend.
4. **AI Extraction** — the backend splits the rows into batches (default 15 rows/batch)
   and sends each batch to Claude with strict mapping instructions (allowed
   `crm_status` values, allowed `data_source` values, date-format rules, handling of
   multiple emails/phones, and skip-if-no-contact-info rules).
5. **Result** — the backend returns structured JSON with the mapped records, skipped
   records (and why), and totals. The frontend renders this as a second table.

## Tech stack

- **Backend:** Python, Flask, Anthropic Python SDK
- **Frontend:** Plain HTML/CSS/JS (no build step needed) + PapaParse (CSV parsing,
  loaded from CDN)
- Single Flask app serves both the API and the static frontend, so there is only
  **one thing to deploy**.

## Project structure

```
groweasy-csv-importer/
├── backend/
│   ├── app.py              # Flask app + AI mapping logic
│   ├── requirements.txt
│   ├── Procfile             # tells hosting providers how to start the app
│   ├── .env.example
│   └── static/
│       └── index.html      # the entire frontend (upload/preview/confirm/results)
├── sample_data/
│   └── sample_leads.csv    # messy test CSV you can use to try the app
├── .gitignore
└── README.md
```

## Running locally

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # get one from console.anthropic.com
python app.py
```

Then open **http://localhost:5000** in your browser.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Your Claude API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-5` | Which Claude model to call |
| `BATCH_SIZE` | No | `15` | Rows sent to the AI per call |
| `PORT` | No | `5000` | Port the server listens on |

## API

### `POST /api/import`
- Body: `multipart/form-data` with a `file` field containing the `.csv`
- Response:
```json
{
  "records": [ { "created_at": "...", "name": "...", "...": "..." } ],
  "skipped": [ { "raw": { "...original columns...": "..." }, "reason": "..." } ],
  "total_imported": 12,
  "total_skipped": 1,
  "total_input_rows": 13
}
```

### `GET /api/health`
Simple health/readiness check, also reports whether the API key is configured.

## Deployment

See `DEPLOYMENT_GUIDE.md` for a click-by-click walkthrough (written for someone
who has never deployed an app before).
