"""
scrapers/__init__.py
Registry mapping vendor config keys to scraper classes.
Add new vendors here after creating their scraper file.
"""

from scrapers.walmart import WalmartScraper
from scrapers.costco import CostcoScraper
from scrapers.amazon import AmazonScraper
from scrapers.target import TargetScraper

SCRAPER_REGISTRY = {
    "walmart": WalmartScraper,
    "costco": CostcoScraper,
    "amazon": AmazonScraper,
    "target": TargetScraper,
}


def get_scraper(vendor_key: str, vendor_cfg: dict, apify_token: str):
    cls = SCRAPER_REGISTRY.get(vendor_key)
    if not cls:
        raise ValueError(f"No scraper registered for vendor: '{vendor_key}'. "
                         f"Add it to scrapers/__init__.py.")
    return cls(vendor_cfg, apify_token)
