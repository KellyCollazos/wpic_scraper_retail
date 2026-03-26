"""
utils/apify_client.py
Thin wrapper around the Apify REST API.
All vendor scrapers call this — they never hit Apify directly.
"""

import time
import requests
from utils.helpers import get_logger

log = get_logger("apify")

APIFY_BASE = "https://api.apify.com/v2"


class ApifyClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("APIFY_TOKEN is not set. Add it to config.yaml or env.")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    # ── Run an actor and wait for results ────────────────────────

    def run_actor(
        self,
        actor_id: str,
        run_input: dict,
        timeout_secs: int = 300,
        poll_interval: int = 10,
    ) -> list[dict]:
        """
        Start an Apify actor run, wait for it to finish, return dataset items.

        Args:
            actor_id:     e.g. "apify/walmart-scraper"
            run_input:    dict passed as the actor's input JSON
            timeout_secs: max seconds to wait before giving up
            poll_interval: seconds between status checks

        Returns:
            List of result dicts from the actor's default dataset.
        """
        log.info(f"Starting Apify actor: {actor_id}")

        # 1. Start the run
        run = self._start_run(actor_id, run_input)
        run_id = run["id"]
        log.info(f"Run started: {run_id}")

        # 2. Poll until finished
        elapsed = 0
        while elapsed < timeout_secs:
            status = self._get_run_status(run_id)
            log.info(f"  Status: {status}  ({elapsed}s elapsed)")
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify run {run_id} ended with status: {status}")
            time.sleep(poll_interval)
            elapsed += poll_interval
        else:
            raise TimeoutError(f"Apify run {run_id} did not finish within {timeout_secs}s")

        # 3. Fetch results
        dataset_id = self._get_dataset_id(run_id)
        items = self._fetch_dataset(dataset_id)
        log.info(f"Fetched {len(items)} items from dataset {dataset_id}")
        return items

    # ── Internal helpers ─────────────────────────────────────────

    def _start_run(self, actor_id: str, run_input: dict) -> dict:
        url = f"{APIFY_BASE}/acts/{actor_id.replace('/', '~')}/runs"
        resp = self.session.post(url, json=run_input, timeout=30)
        resp.raise_for_status()
        return resp.json()["data"]

    def _get_run_status(self, run_id: str) -> str:
        url = f"{APIFY_BASE}/actor-runs/{run_id}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["data"]["status"]

    def _get_dataset_id(self, run_id: str) -> str:
        url = f"{APIFY_BASE}/actor-runs/{run_id}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["data"]["defaultDatasetId"]

    def _fetch_dataset(self, dataset_id: str, limit: int = 50000) -> list[dict]:
        url = f"{APIFY_BASE}/datasets/{dataset_id}/items"
        params = {"format": "json", "limit": limit, "clean": True}
        resp = self.session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
