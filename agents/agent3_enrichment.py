"""
agents/agent3_enrichment.py
────────────────────────────
Agent 3 — Enrichment (Claude ICP scoring + data fill).

What it does:
  1. Reads all rows from every raw_{vendor} sheet
  2. Skips rows already in master_enriched (by source_id + vendor)
  3. Sends each new company to Claude API for ICP scoring
  4. Writes enriched rows to master_enriched sheet
  5. Triggers Excel export when done

Run it:
    python -m agents.agent3_enrichment

Run after Agent 1 (full baseline) or Agent 2 (after each delta run).
Safe to re-run — skips already-enriched companies.
"""

from utils.helpers import (
    load_config, get_logger, get_sheets_client,
    get_or_create_sheet, sheet_to_records, append_rows,
    write_state, timestamp_now,
)
from utils.schema import CompanyRecord, RAW_HEADERS, ENRICHED_HEADERS
from utils.claude_scorer import ClaudeScorer
from output.export_excel import export_to_excel

log = get_logger("agent3")


def run():
    cfg = load_config()
    gs_cfg = cfg["google_sheets"]
    scoring_cfg = cfg["claude_scoring"]
    apify_token = cfg["apis"]["apify_token"]

    log.info("=== Agent 3: Enrichment + ICP Scoring ===")

    gc = get_sheets_client(gs_cfg["credentials_file"])
    spreadsheet = gc.open_by_key(gs_cfg["spreadsheet_id"])

    # Init Claude scorer
    scorer = ClaudeScorer(
        api_key=cfg["apis"]["anthropic_api_key"],
        model=scoring_cfg["model"],
        criteria=scoring_cfg["icp_criteria"],
    )

    # Load master_enriched to know what's already done
    enriched_ws = get_or_create_sheet(spreadsheet, gs_cfg["enriched_sheet"])
    enriched_records = sheet_to_records(enriched_ws)

    # Build dedup set: "vendor::source_id"
    enriched_ids = {
        f"{r.get('vendor', '')}::{r.get('source_id', '')}".lower()
        for r in enriched_records
    }
    log.info(f"Already enriched: {len(enriched_ids)} records")

    total_enriched = 0
    vendors = cfg["vendors"]

    for vendor_key, vendor_cfg in vendors.items():
        if not vendor_cfg.get("enabled", False):
            continue

        log.info(f"\n── Enriching: {vendor_cfg['display_name']} ──")

        sheet_title = gs_cfg["raw_sheet_prefix"] + vendor_key
        try:
            raw_ws = get_or_create_sheet(spreadsheet, sheet_title)
            raw_records = sheet_to_records(raw_ws)
        except Exception as e:
            log.warning(f"Could not read {sheet_title}: {e}")
            continue

        # Filter to unenriched companies
        to_enrich = []
        for row in raw_records:
            uid = f"{row.get('vendor', vendor_cfg['display_name'])}::{row.get('source_id', '')}".lower()
            if uid not in enriched_ids:
                to_enrich.append(row)

        log.info(f"{len(to_enrich)} new companies to enrich")

        if not to_enrich:
            continue

        # Score with Claude in batches
        scored = scorer.score_batch(to_enrich)

        # Write enriched rows to master_enriched
        new_rows = []
        for item in scored:
            record = CompanyRecord.from_dict(item)
            record.enriched_at = timestamp_now()
            if not record.vendor:
                record.vendor = vendor_cfg["display_name"]
            new_rows.append(record.to_enriched_row())

        # Write header if first time
        existing = enriched_ws.get_all_values()
        if not existing:
            enriched_ws.append_row(ENRICHED_HEADERS)

        append_rows(enriched_ws, new_rows)
        log.info(f"Wrote {len(new_rows)} enriched rows")
        total_enriched += len(new_rows)

        write_state(
            spreadsheet, gs_cfg["state_sheet"],
            f"last_enriched_{vendor_key}", timestamp_now()
        )

    log.info(f"\n=== Done. Total enriched this run: {total_enriched} ===")

    # Auto-export Excel
    if cfg["output"].get("auto_export_after_enrich") and total_enriched > 0:
        log.info("Exporting Excel...")
        export_to_excel(spreadsheet, cfg)
        log.info(f"Excel saved to: {cfg['output']['excel_path']}")


if __name__ == "__main__":
    run()
