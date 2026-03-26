"""
scrapers/base_scraper.py
Base class every vendor scraper extends.
Each vendor only needs to implement: build_actor_input() and normalize_item().

Category filtering:
  Set `category_filter` in config.yaml per vendor.
  If the list is empty or missing, ALL categories are kept.
  Matching is fuzzy (keyword-in-string) so "vitamins" matches
  "Vitamins & Supplements", "Vitamin C", etc.
"""

from abc import ABC, abstractmethod
from utils.helpers import get_logger, timestamp_now
from utils.apify_client import ApifyClient
from utils.schema import CompanyRecord


class BaseScraper(ABC):
    """
    Extend this class for each vendor.

    Subclass must implement:
        build_actor_input(max_items) -> dict
        normalize_item(raw_item) -> CompanyRecord | None
    """

    def __init__(self, vendor_cfg: dict, apify_token: str):
        self.cfg = vendor_cfg
        self.vendor_name = vendor_cfg["display_name"]
        self.actor_id = vendor_cfg["apify_actor_id"]
        self.max_items = vendor_cfg.get("max_items", 1000)
        self.dedup_key = vendor_cfg.get("dedup_key", "company_name")
        self.client = ApifyClient(apify_token)
        self.log = get_logger(f"scraper.{self.vendor_name.lower()}")

        # Category filter: list of lowercase keywords from config
        raw_filters = vendor_cfg.get("category_filter", [])
        self.category_filter = [kw.lower().strip() for kw in raw_filters if kw]
        if self.category_filter:
            self.log.info(f"Category filter active: {self.category_filter}")
        else:
            self.log.info("No category filter — keeping all categories")

    @abstractmethod
    def build_actor_input(self, max_items: int) -> dict:
        """Return the input dict for the Apify actor run."""
        ...

    @abstractmethod
    def normalize_item(self, raw_item: dict) -> CompanyRecord | None:
        """
        Map one raw Apify result item to a CompanyRecord.
        Return None to skip the item (e.g. missing required fields).
        """
        ...

    # ── Category matching ─────────────────────────────────────────

    def _passes_category_filter(self, record: CompanyRecord) -> bool:
        """
        Returns True if the record's category matches any filter keyword,
        OR if no filter is configured (keep everything).

        Matching is case-insensitive substring — "vitamins" will match:
          "Vitamins & Supplements", "Vitamin C Products", "Multivitamins", etc.
        """
        if not self.category_filter:
            return True  # no filter = keep all

        category_text = record.category.lower()
        name_text = record.company_name.lower()

        for keyword in self.category_filter:
            if keyword in category_text or keyword in name_text:
                return True

        return False

    # ── Main scrape method ────────────────────────────────────────

    def scrape(self, existing_ids: set | None = None) -> list[CompanyRecord]:
        """
        Run the Apify actor, normalize results, apply category filter,
        and remove already-known IDs.

        Args:
            existing_ids: set of source_id values already in Sheets.
                          Pass None to return everything (full scrape).

        Returns:
            List of CompanyRecord objects that passed all filters.
        """
        self.log.info(f"Scraping {self.vendor_name} (max_items={self.max_items})")

        actor_input = self.build_actor_input(self.max_items)
        raw_items = self.client.run_actor(
            self.actor_id, actor_input, timeout_secs=600
        )
        self.log.info(f"Received {len(raw_items)} raw items from Apify")

        records = []
        skipped_parse = 0       # normalize_item returned None
        skipped_category = 0    # failed category filter
        skipped_dedup = 0       # already in Sheets

        for item in raw_items:
            # 1. Normalize raw Apify item → CompanyRecord
            record = self.normalize_item(item)
            if record is None:
                skipped_parse += 1
                continue

            record.vendor = self.vendor_name
            record.date_scraped = timestamp_now()

            # 2. Category filter
            if not self._passes_category_filter(record):
                skipped_category += 1
                continue

            # 3. Dedup against existing Sheets data
            if existing_ids is not None:
                key = str(record.source_id).lower().strip()
                if key in existing_ids:
                    skipped_dedup += 1
                    continue

            record.is_new = True
            records.append(record)

        self.log.info(
            f"Done — {len(records)} kept | "
            f"{skipped_category} filtered by category | "
            f"{skipped_dedup} duplicates | "
            f"{skipped_parse} unparseable"
        )
        return records
