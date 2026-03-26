"""
scrapers/walmart.py
Walmart vendor scraper — calls Apify's Walmart actor.
Only needs to implement build_actor_input() and normalize_item().
"""

from scrapers.base_scraper import BaseScraper
from utils.schema import CompanyRecord


class WalmartScraper(BaseScraper):

    def build_actor_input(self, max_items: int) -> dict:
        return {
            "search": "",                        # leave empty to browse all sellers
            "maxItems": max_items,
            "scrapeType": self.cfg.get("scrape_type", "sellers"),
            "proxyConfiguration": {"useApifyProxy": True},
        }

    def normalize_item(self, item: dict) -> CompanyRecord | None:
        name = item.get("sellerName") or item.get("name") or ""
        if not name:
            return None

        return CompanyRecord(
            company_name=name.strip(),
            source_id=str(item.get("sellerId") or item.get("id") or name),
            category=item.get("category") or item.get("productCategory") or "",
            listing_url=item.get("url") or item.get("productUrl") or "",
            website=item.get("website") or "",
            description=item.get("description") or "",
            hq_country="US",              # Walmart sellers are predominantly US
        )
