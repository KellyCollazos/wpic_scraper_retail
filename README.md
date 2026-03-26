# Vendor Scraper System

Hands-free scraper that finds brands listed on Walmart, Costco, Amazon, and Target,
scores them for WPIC ICP fit using Claude, and exports a formatted Excel file.

---

## Stack

| Layer        | Tool                          |
|--------------|-------------------------------|
| Scraping     | Apify (managed actors)        |
| ICP Scoring  | Claude API (Haiku — fast)     |
| Storage      | Google Sheets                 |
| Scheduling   | Google Apps Script (monthly)  |
| Output       | Excel (.xlsx via openpyxl)    |

---

## Setup

### 1. Install dependencies
```bash
cd vendor-scraper
pip install -r requirements.txt
```

### 2. Get your API keys
- **Apify**: https://console.apify.com/account/integrations → copy API token
- **Anthropic**: https://console.anthropic.com → API keys → create key
- **Google Sheets**: Create a service account → download JSON credentials

### 3. Set up Google Sheets
1. Create a new Google Spreadsheet
2. Copy the spreadsheet ID from the URL: `docs.google.com/spreadsheets/d/{ID}/edit`
3. Share the spreadsheet with your service account email (Editor access)

### 4. Fill in config.yaml
```yaml
apis:
  apify_token: "your_token_here"
  anthropic_api_key: "your_key_here"

google_sheets:
  spreadsheet_id: "your_spreadsheet_id_here"
  credentials_file: "config/google_credentials.json"
```

Or use environment variables (safer — keeps secrets out of config files):
```bash
export APIFY_TOKEN="your_token"
export ANTHROPIC_API_KEY="your_key"
```

### 5. Place Google credentials file
Copy your service account JSON file to:
```
config/google_credentials.json
```

---

## Run Order

### First time — run once to build the baseline:
```bash
python -m agents.agent1_full_scrape
python -m agents.agent3_enrichment
```

### Monthly — run on a schedule (Agent 2 → Agent 3):
```bash
python -m agents.agent2_delta_scrape
python -m agents.agent3_enrichment
```

### Export Excel manually anytime:
```bash
python -m output.export_excel
```

---

## File Structure

```
vendor-scraper/
├── agents/
│   ├── agent1_full_scrape.py    # Run once — full baseline scrape
│   ├── agent2_delta_scrape.py   # Run monthly — new companies only
│   └── agent3_enrichment.py     # Run after each scrape — Claude ICP scoring
│
├── scrapers/
│   ├── base_scraper.py          # Base class all vendors extend
│   ├── walmart.py
│   ├── costco.py
│   ├── amazon.py
│   ├── target.py
│   └── __init__.py              # Registry — add new vendors here
│
├── utils/
│   ├── helpers.py               # Config, Sheets client, state, logging
│   ├── apify_client.py          # Apify REST API wrapper
│   ├── claude_scorer.py         # Claude ICP scoring
│   └── schema.py                # Canonical data schema (CompanyRecord)
│
├── output/
│   └── export_excel.py          # Exports master_enriched → .xlsx
│
├── config/
│   ├── config.yaml              # Master config — edit this
│   └── google_credentials.json  # Your service account key (gitignored)
│
├── state/                       # Local state cache (optional)
├── output/                      # Excel files saved here
└── requirements.txt
```

---

## Adding a New Vendor

1. Create `scrapers/new_vendor.py` extending `BaseScraper`
2. Implement `build_actor_input()` and `normalize_item()`
3. Register it in `scrapers/__init__.py`
4. Add vendor config block in `config/config.yaml`

That's it — all three agents will pick it up automatically.

---

## Google Sheets Layout

| Tab               | Contents                                      |
|-------------------|-----------------------------------------------|
| `raw_walmart`     | Raw scraped companies from Walmart            |
| `raw_costco`      | Raw scraped companies from Costco             |
| `raw_amazon`      | Raw scraped companies from Amazon             |
| `raw_target`      | Raw scraped companies from Target             |
| `master_enriched` | All companies post-ICP scoring                |
| `system_state`    | Run timestamps, row counts                    |

---

## Excel Output

`output/vendor_companies.xlsx` contains:
- **Summary** sheet (tab 1) — totals + tier breakdown per vendor
- One sheet per vendor, sorted by ICP score descending
- Rows color-coded by tier: A (green), B (blue), C (amber), D (red)
