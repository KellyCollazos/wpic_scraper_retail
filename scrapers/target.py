"""
scrapers/target.py
Target brand scraper — uses Apify generic web scraper on Target's brand directory.
"""

from scrapers.base_scraper import BaseScraper
from utils.schema import CompanyRecord


class TargetScraper(BaseScraper):

    def build_actor_input(self, max_items: int) -> dict:
        return {
            "startUrls": [{"url": self.cfg.get("start_url", "https://www.target.com/brands")}],
            "maxPagesPerCrawl": 30,
            "maxResultsPerCrawl": max_items,
            "pageFunction": """
                async function pageFunction(context) {
                    const { $, request } = context;
                    const brands = [];
                    $('a[href*="/b/"]').each((i, el) => {
                        const name = $(el).text().trim();
                        const href = $(el).attr('href');
                        if (name && href && href.includes('/b/')) {
                            const slug = href.split('/b/')[1]?.split('?')[0] || '';
                            brands.push({
                                brand_name: name,
                                brand_slug: slug,
                                listing_url: 'https://www.target.com' + href,
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
            source_id=item.get("brand_slug") or name.lower().strip().replace(" ", "_"),
            category=item.get("category") or "",
            listing_url=item.get("listing_url") or item.get("url") or "",
            website="",
            description="",
            hq_country="",
        )
