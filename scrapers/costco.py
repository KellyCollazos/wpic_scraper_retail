"""
scrapers/costco.py
Costco brand scraper — uses Apify's generic web scraper.
Costco's brand directory is simpler HTML, no dedicated actor needed.
"""

from scrapers.base_scraper import BaseScraper
from utils.schema import CompanyRecord


class CostcoScraper(BaseScraper):

    def build_actor_input(self, max_items: int) -> dict:
        return {
            "startUrls": [{"url": self.cfg.get("start_url", "https://www.costco.com/brands.html")}],
            "maxPagesPerCrawl": 50,
            "maxResultsPerCrawl": max_items,
            "pageFunction": """
                async function pageFunction(context) {
                    const { $, request } = context;
                    const brands = [];
                    $('a[href*="/brand/"]').each((i, el) => {
                        const name = $(el).text().trim();
                        const href = $(el).attr('href');
                        if (name) {
                            brands.push({
                                brand_name: name,
                                listing_url: href ? 'https://www.costco.com' + href : '',
                                category: $(el).closest('[data-category]').data('category') || ''
                            });
                        }
                    });
                    return brands;
                }
            """,
            "proxyConfiguration": {"useApifyProxy": True},
        }

    def normalize_item(self, item: dict) -> CompanyRecord | None:
        name = item.get("brand_name") or item.get("name") or ""
        if not name:
            return None

        return CompanyRecord(
            company_name=name.strip(),
            source_id=name.lower().strip().replace(" ", "_"),
            category=item.get("category") or "",
            listing_url=item.get("listing_url") or item.get("url") or "",
            website="",             # enrichment agent fills this
            description="",
            hq_country="",          # enrichment agent fills this
        )
