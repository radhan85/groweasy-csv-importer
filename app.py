"""
GrowEasy AI CSV Importer - Backend
-----------------------------------
Accepts a CSV file of leads in ANY format/layout, and uses an LLM (Anthropic Claude)
to intelligently map the columns into the fixed GrowEasy CRM schema, batch by batch.

Endpoints:
  GET  /                -> serves the frontend (static/index.html)
  POST /api/import      -> accepts a CSV file, returns AI-extracted CRM records as JSON

Run locally:
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=sk-ant-...
  python app.py
"""

import os
import csv
import io
import json
import logging
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("groweasy-importer")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_NAME = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "15"))          # rows sent to the AI per call
MAX_FILE_SIZE_MB = 10

ALLOWED_CRM_STATUS = {
    "GOOD_LEAD_FOLLOW_UP",
    "DID_NOT_CONNECT",
    "BAD_LEAD",
    "SALE_DONE",
}

ALLOWED_DATA_SOURCE = {
    "leads_on_demand",
    "meridian_tower",
    "eden_park",
    "varah_swamy",
    "sarjapur_plots",
}

CRM_FIELDS = [
    "created_at",
    "name",
    "email",
    "country_code",
    "mobile_without_country_code",
    "company",
    "city",
    "state",
    "country",
    "lead_owner",
    "crm_status",
    "crm_note",
    "data_source",
    "possession_time",
    "description",
]

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = f"""You are a data-mapping engine for a CRM system called GrowEasy.

You will receive a batch of raw lead records extracted from an arbitrary CSV file.
The CSV may come from Facebook Lead Ads, Google Ads, Excel exports, real-estate CRMs,
sales reports, marketing agency exports, or manually created spreadsheets. Column
names, layout, and structure are NOT fixed and can vary wildly between files.

Your job: intelligently map each raw record into this EXACT target schema, using your
best judgement about which raw column(s) correspond to which target field, even if the
raw column names are abbreviated, differently worded, or absent.

TARGET SCHEMA (use exactly these keys, all of them, for every record):
{json.dumps(CRM_FIELDS)}

RULES YOU MUST FOLLOW EXACTLY:

1. crm_status - Only ever use one of: {sorted(ALLOWED_CRM_STATUS)}. If no confident
   match can be inferred from the raw data (e.g. a status/remarks column), leave it as
   an empty string "".

2. data_source - Only ever use one of: {sorted(ALLOWED_DATA_SOURCE)}. If none match
   confidently, leave it as an empty string "".

3. created_at - Must be a value that JavaScript's `new Date(created_at)` can parse
   correctly (e.g. "2026-05-13 14:20:48" or ISO 8601). If no date is present in the
   raw record, leave it as an empty string "".

4. crm_note - Use this field to capture: remarks, follow-up notes, additional
   comments, extra phone numbers, extra email addresses, and any other useful
   information from the raw record that doesn't fit any other target field.
   Concatenate multiple pieces of info with "; ".

5. Multiple emails or mobile numbers - If a raw record has multiple email addresses,
   use only the FIRST one as `email` and append the rest into crm_note (e.g.
   "Additional emails: a@x.com, b@x.com"). Do the same for mobile numbers:
   first number -> mobile_without_country_code, rest -> appended to crm_note.

6. CSV/JSON safety - Never include raw newline characters inside any field value.
   If a value naturally contains a line break, replace it with the literal
   two characters backslash-n ("\\n") instead of an actual newline.

7. Skip invalid records - If a record contains NEITHER an email address NOR a mobile
   number anywhere in its raw data, do not include it in "records". Instead include
   it (unchanged, as a dict of its original raw fields) in a "skipped" list, along
   with a short "reason" string.

8. Every other target field you cannot confidently determine should be an empty
   string "" (never null, never omit the key).

9. country_code should be a phone country code like "+91" if determinable, else "".

OUTPUT FORMAT - respond with ONLY valid JSON (no markdown fences, no commentary),
exactly matching this shape:

{{
  "records": [ {{ ...all {len(CRM_FIELDS)} target fields as strings... }}, ... ],
  "skipped": [ {{ "raw": {{...original raw record...}}, "reason": "..." }}, ... ]
}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_csv(file_stream) -> list[dict]:
    """Parse an uploaded CSV file (any column layout) into a list of dict rows."""
    raw_bytes = file_stream.read()
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(row) for row in reader]
    return rows


def chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def call_ai_for_batch(batch: list[dict]) -> dict:
    """Send one batch of raw rows to Claude and get back mapped CRM records."""
    if client is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set on the server. Add it in your hosting "
            "provider's environment variables."
        )

    user_content = (
        "Here is a batch of raw lead records (as a JSON array of objects, straight "
        "from a CSV file). Map every record into the target CRM schema per your "
        "instructions.\n\nRAW RECORDS:\n" + json.dumps(batch, ensure_ascii=False)
    )

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    text = text.strip()

    # Defensive cleanup in case the model wraps output in markdown fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON: %s\nRaw text: %s", e, text)
        raise RuntimeError("AI returned an invalid response for this batch.")

    return parsed


def sanitize_record(record: dict) -> dict:
    """Ensure record has all required fields, correct enum values, and no raw newlines."""
    clean = {}
    for field in CRM_FIELDS:
        value = record.get(field, "")
        if value is None:
            value = ""
        value = str(value).replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
        clean[field] = value

    if clean["crm_status"] not in ALLOWED_CRM_STATUS:
        clean["crm_status"] = ""
    if clean["data_source"] not in ALLOWED_DATA_SOURCE:
        clean["data_source"] = ""

    return clean


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "ai_configured": client is not None})


@app.route("/api/import", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Field name must be 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files are supported."}), 400

    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE_MB}MB)."}), 400

    try:
        raw_rows = parse_csv(file)
    except Exception as e:
        logger.exception("CSV parse failure")
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    if not raw_rows:
        return jsonify({"error": "CSV file has no data rows."}), 400

    all_records = []
    all_skipped = []
    errors = []

    for batch in chunk(raw_rows, BATCH_SIZE):
        try:
            result = call_ai_for_batch(batch)
        except Exception as e:
            logger.exception("Batch failed")
            errors.append(str(e))
            # Treat the whole failed batch as skipped, so the user still gets a result
            for r in batch:
                all_skipped.append({"raw": r, "reason": f"AI processing error: {e}"})
            continue

        for rec in result.get("records", []):
            all_records.append(sanitize_record(rec))

        for skip in result.get("skipped", []):
            all_skipped.append(skip)

    response_payload = {
        "records": all_records,
        "skipped": all_skipped,
        "total_imported": len(all_records),
        "total_skipped": len(all_skipped),
        "total_input_rows": len(raw_rows),
    }
    if errors:
        response_payload["warnings"] = errors

    return jsonify(response_payload)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
