"""
scrapers/amazon.py
Amazon seller/brand scraper — calls Apify's Amazon crawler.
"""

from scrapers.base_scraper import BaseScraper
from utils.schema import CompanyRecord


class AmazonScraper(BaseScraper):

    def build_actor_input(self, max_items: int) -> dict:
        return {
            "startUrls": [
                {"url": "https://www.amazon.com/gp/browse.html?node=2619526011"}  # Brands store
            ],
            "maxItems": max_items,
            "scrapeType": self.cfg.get("scrape_type", "sellers"),
            "proxyConfiguration": {"useApifyProxy": True},
            "useStealth": True,      # Amazon has strong bot detection
        }

    def normalize_item(self, item: dict) -> CompanyRecord | None:
        name = item.get("sellerName") or item.get("brandName") or item.get("name") or ""
        if not name:
            return None

        return CompanyRecord(
            company_name=name.strip(),
            source_id=str(item.get("sellerId") or item.get("brandId") or name),
            category=item.get("category") or item.get("browseNode") or "",
            listing_url=item.get("sellerUrl") or item.get("brandUrl") or item.get("url") or "",
            website=item.get("website") or "",
            description=item.get("description") or item.get("about") or "",
            hq_country=item.get("country") or "",
        )
