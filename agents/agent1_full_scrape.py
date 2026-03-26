"""
agents/agent1_full_scrape.py
────────────────────────────
Agent 1 — Full Scrape (runs ONCE to build the baseline).

What it does:
  1. Loops over every enabled vendor in config.yaml
  2. Runs the Apify actor for that vendor
  3. Writes all results to the raw_{vendor} tab in Google Sheets
  4. Records the run timestamp in the state sheet

Run it:
    python -m agents.agent1_full_scrape

Re-running is safe — it will overwrite the raw sheet, not append.
"""

import sys
from utils.helpers import load_config, get_logger, get_sheets_client
from utils.helpers import get_or_create_sheet, append_rows, write_state, timestamp_now
from utils.schema import RAW_HEADERS
from scrapers import get_scraper

log = get_logger("agent1")


def run():
    cfg = load_config()
    vendors = cfg["vendors"]
    apify_token = cfg["apis"]["apify_token"]
    gs_cfg = cfg["google_sheets"]

    log.info("=== Agent 1: Full Scrape ===")

    # Connect to Google Sheets
    gc = get_sheets_client(gs_cfg["credentials_file"])
    spreadsheet = gc.open_by_key(gs_cfg["spreadsheet_id"])

    total_new = 0

    for vendor_key, vendor_cfg in vendors.items():
        if not vendor_cfg.get("enabled", False):
            log.info(f"Skipping disabled vendor: {vendor_key}")
            continue

        log.info(f"\n── Vendor: {vendor_cfg['display_name']} ──")

        try:
            scraper = get_scraper(vendor_key, vendor_cfg, apify_token)

            # Full scrape = no existing_ids filter (get everything)
            records = scraper.scrape(existing_ids=None)

            if not records:
                log.warning(f"No records returned for {vendor_key}")
                continue

            # Write to raw_{vendor} sheet (clear first, then write fresh)
            sheet_title = gs_cfg["raw_sheet_prefix"] + vendor_key
            ws = get_or_create_sheet(spreadsheet, sheet_title)
            ws.clear()
            ws.append_row(RAW_HEADERS)
            rows = [r.to_raw_row() for r in records]
            append_rows(ws, rows)

            log.info(f"Wrote {len(rows)} rows to sheet: {sheet_title}")
            total_new += len(rows)

            # Update state
            write_state(
                spreadsheet,
                gs_cfg["state_sheet"],
                f"last_full_scrape_{vendor_key}",
                timestamp_now(),
            )
            write_state(
                spreadsheet,
                gs_cfg["state_sheet"],
                f"row_count_{vendor_key}",
                str(len(rows)),
            )

        except Exception as e:
            log.error(f"Failed scraping {vendor_key}: {e}", exc_info=True)
            continue

    log.info(f"\n=== Done. Total rows written: {total_new} ===")


if __name__ == "__main__":
    run()
