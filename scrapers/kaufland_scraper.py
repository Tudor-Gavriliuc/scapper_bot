from typing import Dict, List, Optional, Tuple
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core.normalizer import clean_text
from scrapers.base_scraper import BaseScraper


class KauflandScraper(BaseScraper):
    source_code = "kaufland"
    source_name = "Kaufland"

    def scrape(self) -> List[Dict]:
        html = self._get_page_html()
        if not html:
            print("[WARN] Kaufland HTML is empty.")
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.settings.kaufland_product_card_selector)

        # If static HTML has no cards, retry with Playwright when enabled.
        if not cards and self.settings.use_playwright:
            print("[INFO] No cards in static HTML. Retrying Kaufland with Playwright.")
            js_html = self._fetch_with_playwright(self.settings.kaufland_url)
            if js_html:
                soup = BeautifulSoup(js_html, "html.parser")
                cards = soup.select(self.settings.kaufland_product_card_selector)

        if not cards:
            print(
                "[INFO] No Kaufland products found. "
                "Check selectors in .env if page structure changed."
            )
            return []

        valid_from, valid_to = self._extract_validity_dates(soup)

        products: List[Dict] = []
        for card in cards:
            name = self._get_text(card, self.settings.kaufland_name_selector)
            new_price = self._get_text(card, self.settings.kaufland_new_price_selector)
            old_price = self._get_text(card, self.settings.kaufland_old_price_selector)
            discount = self._get_text(card, self.settings.kaufland_discount_selector)
            category = self._get_text(card, self.settings.kaufland_category_selector)
            # valid_from / valid_to are page-level, extracted once above

            image_url = ""
            image_tag = card.select_one(self.settings.kaufland_image_selector)
            if image_tag:
                image_url = clean_text(
                    image_tag.get("src")
                    or image_tag.get("data-src")
                    or image_tag.get("srcset")
                )
                if image_url:
                    image_url = urljoin(self.settings.kaufland_base_url, image_url)

            product_url = ""
            link_tag = card.select_one(self.settings.kaufland_link_selector)
            if link_tag:
                href = clean_text(link_tag.get("href"))
                if href:
                    product_url = urljoin(self.settings.kaufland_base_url, href)

            products.append(
                {
                    "source_code": self.source_code,
                    "source_name": self.source_name,
                    "name": name,
                    "new_price": new_price,
                    "old_price": old_price,
                    "discount": discount,
                    "category": category,
                    "image_url": image_url,
                    "product_url": product_url,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                }
            )

        print(f"[INFO] Kaufland scraped products: {len(products)}")
        return products

    def _extract_validity_dates(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """Extract the page-level validity period (e.g. '30.04.2026 - 06.05.2026')."""
        date_range_re = re.compile(
            r'(\d{1,2}\.\d{2}\.\d{4})\s*[-–]\s*(\d{1,2}\.\d{2}\.\d{4})'
        )
        for tag in soup.find_all(True):
            text = tag.get_text(" ", strip=True)
            m = date_range_re.search(text)
            if m:
                return m.group(1), m.group(2)
        return "", ""

    def _get_page_html(self) -> Optional[str]:
        html = self.fetch_html(self.settings.kaufland_url)
        if html:
            return html
        return None

    def _get_text(self, element, selector: str) -> str:
        node = element.select_one(selector)
        return clean_text(node.get_text(" ", strip=True) if node else "")

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[ERROR] Playwright is not installed.")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.settings.request_timeout_seconds * 1000)
                page.wait_for_timeout(2500)
                html = page.content()
                browser.close()
                return html
        except Exception as exc:
            print(f"[ERROR] Playwright fetch failed for {url}: {exc}")
            return None
