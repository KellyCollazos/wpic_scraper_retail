"""
utils/helpers.py
Shared utilities used by all agents: config loader, Google Sheets client, logger.
"""

import os
import json
import logging
import yaml
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# ── Logger ────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


# ── Config ────────────────────────────────────────────────────────

def load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    # Allow env vars to override API keys so secrets stay out of config.yaml
    cfg["apis"]["apify_token"] = (
        os.getenv("APIFY_TOKEN") or cfg["apis"].get("apify_token", "")
    )
    cfg["apis"]["anthropic_api_key"] = (
        os.getenv("ANTHROPIC_API_KEY") or cfg["apis"].get("anthropic_api_key", "")
    )
    return cfg


# ── Google Sheets ─────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheets_client(credentials_file: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_sheet(spreadsheet, title: str):
    """Return worksheet by title, creating it if it doesn't exist."""
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=10000, cols=30)


def sheet_to_records(ws) -> list[dict]:
    """Return all rows as list of dicts (first row = headers)."""
    return ws.get_all_records()


def append_rows(ws, rows: list[list], header: list[str] | None = None):
    """
    Append rows to a worksheet.
    If the sheet is empty and header is provided, write header first.
    """
    existing = ws.get_all_values()
    if not existing and header:
        ws.append_row(header)
    if rows:
        ws.append_rows(rows)


# ── State Management ──────────────────────────────────────────────

def read_state(spreadsheet, state_sheet: str) -> dict:
    """Read system state from the state sheet (last run times, row counts, etc.)."""
    ws = get_or_create_sheet(spreadsheet, state_sheet)
    records = ws.get_all_records()
    state = {}
    for row in records:
        if row.get("key"):
            state[row["key"]] = row.get("value", "")
    return state


def write_state(spreadsheet, state_sheet: str, key: str, value: str):
    """Write or update a key-value pair in the state sheet."""
    ws = get_or_create_sheet(spreadsheet, state_sheet)
    records = ws.get_all_records()
    # Find existing row
    for i, row in enumerate(records, start=2):  # row 1 = header
        if row.get("key") == key:
            ws.update_cell(i, 2, value)
            return
    # Not found — append new row
    if not records:
        ws.append_row(["key", "value", "updated_at"])
    ws.append_row([key, value, datetime.utcnow().isoformat()])


# ── Data Helpers ──────────────────────────────────────────────────

def normalize_company_name(name: str) -> str:
    """Lowercase + strip whitespace for dedup matching."""
    return name.lower().strip() if name else ""


def build_dedup_set(records: list[dict], dedup_key: str) -> set:
    """Build a set of existing dedup keys for fast lookup."""
    return {normalize_company_name(str(r.get(dedup_key, ""))) for r in records}


def timestamp_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
