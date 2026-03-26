"""
utils/schema.py
The canonical data schema every vendor scraper must output.
All scrapers normalize their raw Apify results into this format.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Raw (post-scrape, pre-enrichment) ────────────────────────────

RAW_HEADERS = [
    "company_name",
    "vendor",
    "source_id",
    "category",
    "listing_url",
    "website",
    "description",
    "hq_country",
    "date_scraped",
    "is_new",
]

# ── Enriched (after Claude scoring) ──────────────────────────────

ENRICHED_HEADERS = RAW_HEADERS + [
    "revenue_est",
    "employee_count",
    "icp_score",
    "icp_tier",
    "icp_reason",
    "china_presence_flag",
    "enriched_at",
]


@dataclass
class CompanyRecord:
    # Core identity
    company_name: str = ""
    vendor: str = ""           # "Walmart", "Costco", etc.
    source_id: str = ""        # vendor's internal ID — used for dedup
    category: str = ""
    listing_url: str = ""

    # From scrape (may be empty — enrichment fills these)
    website: str = ""
    description: str = ""
    hq_country: str = ""

    # Scrape metadata
    date_scraped: str = ""
    is_new: bool = True

    # Enrichment fields (filled by Agent 3)
    revenue_est: str = ""
    employee_count: str = ""
    icp_score: int = 0
    icp_tier: str = ""
    icp_reason: str = ""
    china_presence_flag: bool = False
    enriched_at: str = ""

    def to_raw_row(self) -> list:
        """Return values in RAW_HEADERS order for writing to Sheets."""
        d = asdict(self)
        return [d.get(h, "") for h in RAW_HEADERS]

    def to_enriched_row(self) -> list:
        """Return values in ENRICHED_HEADERS order for writing to Sheets."""
        d = asdict(self)
        return [d.get(h, "") for h in ENRICHED_HEADERS]

    @classmethod
    def from_dict(cls, d: dict) -> "CompanyRecord":
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)
