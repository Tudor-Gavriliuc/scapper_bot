from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import requests


class BaseScraper(ABC):
    source_code: str = ""
    source_name: str = ""

    def __init__(self, settings) -> None:
        self.settings = settings

    @abstractmethod
    def scrape(self) -> List[Dict]:
        """Scrape source and return normalized products."""

    def fetch_html(self, url: str) -> Optional[str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            print(f"[ERROR] Request failed for {url}: {exc}")
            return None
