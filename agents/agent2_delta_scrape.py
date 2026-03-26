"""
agents/agent2_delta_scrape.py
──────────────────────────────
Agent 2 — Delta Scrape (runs monthly, new companies only).

What it does:
  1. Reads existing source_ids from each raw_{vendor} sheet
  2. Re-scrapes each enabled vendor via Apify
  3. Filters out anything already in the sheet (dedup by source_id)
  4. Appends ONLY new rows to raw_{vendor}
  5. Updates the state sheet with run timestamp + new count

Run it:
    python -m agents.agent2_delta_scrape

Safe to run manually anytime — it will never duplicate existing records.
Schedule this monthly via Google Apps Script or Make.com.
"""

from utils.helpers import (
    load_config, get_logger, get_sheets_client,
    get_or_create_sheet, sheet_to_records, append_rows,
    write_state, timestamp_now, build_dedup_set,
)
from utils.schema import RAW_HEADERS
from scrapers import get_scraper

log = get_logger("agent2")


def run():
    cfg = load_config()
    vendors = cfg["vendors"]
    apify_token = cfg["apis"]["apify_token"]
    gs_cfg = cfg["google_sheets"]

    log.info("=== Agent 2: Delta Scrape (new companies only) ===")

    gc = get_sheets_client(gs_cfg["credentials_file"])
    spreadsheet = gc.open_by_key(gs_cfg["spreadsheet_id"])

    total_new = 0

    for vendor_key, vendor_cfg in vendors.items():
        if not vendor_cfg.get("enabled", False):
            continue

        log.info(f"\n── Vendor: {vendor_cfg['display_name']} ──")

        try:
            sheet_title = gs_cfg["raw_sheet_prefix"] + vendor_key
            ws = get_or_create_sheet(spreadsheet, sheet_title)

            # Load existing records and build dedup set
            existing_records = sheet_to_records(ws)
            dedup_key = vendor_cfg.get("dedup_key", "company_name")
            existing_ids = build_dedup_set(existing_records, dedup_key)

            log.info(f"Existing records: {len(existing_records)} | Dedup key: {dedup_key}")

            # Scrape with dedup filter — only new items come back
            scraper = get_scraper(vendor_key, vendor_cfg, apify_token)
            new_records = scraper.scrape(existing_ids=existing_ids)

            if not new_records:
                log.info("No new companies found.")
                write_state(
                    spreadsheet, gs_cfg["state_sheet"],
                    f"last_delta_scrape_{vendor_key}", timestamp_now()
                )
                continue

            # Append new rows (do NOT clear — add to bottom)
            rows = [r.to_raw_row() for r in new_records]
            append_rows(ws, rows)

            log.info(f"Appended {len(rows)} new rows to {sheet_title}")
            total_new += len(rows)

            write_state(
                spreadsheet, gs_cfg["state_sheet"],
                f"last_delta_scrape_{vendor_key}", timestamp_now()
            )
            write_state(
                spreadsheet, gs_cfg["state_sheet"],
                f"new_this_run_{vendor_key}", str(len(rows))
            )

        except Exception as e:
            log.error(f"Delta scrape failed for {vendor_key}: {e}", exc_info=True)
            continue

    log.info(f"\n=== Done. Total new companies this run: {total_new} ===")


if __name__ == "__main__":
    run()
