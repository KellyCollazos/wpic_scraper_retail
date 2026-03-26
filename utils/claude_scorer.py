"""
utils/claude_scorer.py
Calls the Claude API to score each company against WPIC's ICP criteria.
Returns a score 1-10 + a one-line reason. Cheap + fast using Haiku.
"""

import json
import anthropic
from utils.helpers import get_logger

log = get_logger("claude_scorer")


class ClaudeScorer:
    def __init__(self, api_key: str, model: str, criteria: dict):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.criteria = criteria

    def score(self, company: dict) -> dict:
        """
        Score a single company dict against WPIC's ICP.

        Input company dict should have at minimum:
            company_name, website (optional), category (optional),
            description (optional), hq_country (optional)

        Returns:
            {
                "icp_score": int (1-10),
                "icp_tier": str ("A" | "B" | "C" | "D"),
                "icp_reason": str (one sentence),
                "china_presence_flag": bool
            }
        """
        prompt = self._build_prompt(company)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            result = json.loads(raw)
            result["icp_tier"] = self._score_to_tier(result.get("icp_score", 0))
            return result

        except Exception as e:
            log.warning(f"Claude scoring failed for {company.get('company_name')}: {e}")
            return {
                "icp_score": 0,
                "icp_tier": "D",
                "icp_reason": "Scoring failed",
                "china_presence_flag": False,
            }

    def score_batch(self, companies: list[dict]) -> list[dict]:
        """Score a list of companies. Returns list with scoring fields added."""
        results = []
        for i, company in enumerate(companies):
            log.info(f"Scoring {i+1}/{len(companies)}: {company.get('company_name', '?')}")
            scores = self.score(company)
            results.append({**company, **scores})
        return results

    # ── Prompt ───────────────────────────────────────────────────

    def _build_prompt(self, company: dict) -> str:
        criteria = self.criteria
        categories = ", ".join(criteria.get("target_categories", []))

        return f"""You are an ICP scorer for WPIC Marketing, which helps North American consumer brands expand into China and APAC markets.

Score this company as a potential WPIC client.

COMPANY DATA:
- Name: {company.get('company_name', 'Unknown')}
- Website: {company.get('website', 'Unknown')}
- Category: {company.get('category', 'Unknown')}
- Description: {company.get('description', 'Unknown')}
- HQ Country: {company.get('hq_country', 'Unknown')}
- Estimated Revenue: {company.get('revenue_est', 'Unknown')}

WPIC'S IDEAL CUSTOMER PROFILE:
- Business model: B2C or DTC brand (NOT a marketplace, distributor, or B2B company)
- Revenue: ${criteria.get('revenue_min_usd', 10000000):,} to ${criteria.get('revenue_max_usd', 500000000):,} USD
- HQ: {', '.join(criteria.get('hq_countries', ['US', 'CA']))}
- NO existing China/Tmall/JD.com/WeChat commerce presence
- Sells physical consumer goods in: {categories}

Respond ONLY with a valid JSON object. No explanation outside the JSON.

{{
  "icp_score": <integer 1-10, where 10 = perfect ICP fit>,
  "icp_reason": "<one sentence explaining the score>",
  "china_presence_flag": <true if company appears to already be in China, else false>
}}"""

    def _score_to_tier(self, score: int) -> str:
        if score >= 8:
            return "A"
        elif score >= 6:
            return "B"
        elif score >= 4:
            return "C"
        else:
            return "D"
