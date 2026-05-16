import json
import math
import os
import time
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from core.normalizer import clean_text
from scrapers.base_scraper import BaseScraper


class MetroScraper(BaseScraper):
    source_code = "metro"
    source_name = "Metro"

    def scrape(self) -> List[Dict]:
        try:
            from DrissionPage import ChromiumOptions, ChromiumPage
        except ImportError:
            print("[ERROR] DrissionPage is not installed. Metro scraper skipped.")
            return []

        options = ChromiumOptions()
        run_in_ci = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
        run_headless = self.settings.metro_headless or run_in_ci

        if run_headless:
            options.set_argument("--headless=new")
            options.set_argument("--disable-gpu")
            options.set_argument("--window-size=1920,1080")
        elif self.settings.metro_start_minimized:
            options.set_argument("--start-minimized")

        if run_in_ci:
            options.set_argument("--no-sandbox")
            options.set_argument("--disable-dev-shm-usage")

        page = ChromiumPage(options)
        products: List[Dict] = []

        try:
            first_html = self._load_page_html(page, 1)
            if not first_html:
                print("[WARN] Metro first page HTML is empty.")
                return []

            first_payload = self._extract_next_data_payload(first_html)
            if not first_payload:
                print("[WARN] Metro __NEXT_DATA__ was not found.")
                return []

            category_data = self._extract_category_data(first_payload)
            if not category_data:
                print("[WARN] Metro categoryData payload missing.")
                return []

            total_count = int(category_data.get("count") or 0)
            first_page_results = category_data.get("results") or []
            page_size = len(first_page_results) if first_page_results else 30
            total_pages = max(1, math.ceil(total_count / max(page_size, 1)))
            if self.settings.metro_max_pages > 0:
                total_pages = min(total_pages, self.settings.metro_max_pages)

            seen_ids = set()

            for item in first_page_results:
                product = self._map_product(item)
                dedupe_id = product["product_url"] or clean_text(item.get("ean"))
                if dedupe_id and dedupe_id in seen_ids:
                    continue
                if dedupe_id:
                    seen_ids.add(dedupe_id)
                products.append(product)

            for page_num in range(2, total_pages + 1):
                html = self._load_page_html(page, page_num)
                if not html:
                    continue

                payload = self._extract_next_data_payload(html)
                if not payload:
                    continue

                page_category_data = self._extract_category_data(payload)
                if not page_category_data:
                    continue

                page_results = page_category_data.get("results") or []
                for item in page_results:
                    product = self._map_product(item)
                    dedupe_id = product["product_url"] or clean_text(item.get("ean"))
                    if dedupe_id and dedupe_id in seen_ids:
                        continue
                    if dedupe_id:
                        seen_ids.add(dedupe_id)
                    products.append(product)

            print(
                "[INFO] Metro scraped products: "
                f"{len(products)} (count={total_count}, pages={total_pages})"
            )
            return products
        finally:
            page.quit()

    def _load_page_html(self, page, page_number: int) -> Optional[str]:
        url = self._build_page_url(self.settings.metro_promotions_url, page_number)
        try:
            page.get(url)
        except Exception as exc:
            print(f"[WARN] Metro page load failed: page={page_number}, err={exc}")
            return None

        wait_s = max(self.settings.metro_page_wait_seconds, 0.0)
        if wait_s > 0:
            time.sleep(wait_s)

        html = page.html or ""
        if "__NEXT_DATA__" not in html:
            # Give one extra chance in case Cloudflare or delayed hydration appeared first.
            time.sleep(1.0)
            html = page.html or ""
        return html

    def _extract_next_data_payload(self, html: str) -> Optional[dict]:
        marker = "__NEXT_DATA__"
        start_marker = html.find(marker)
        if start_marker == -1:
            return None

        script_start = html.rfind("<script", 0, start_marker)
        if script_start == -1:
            return None

        json_start = html.find(">", script_start)
        if json_start == -1:
            return None

        json_end = html.find("</script>", json_start)
        if json_end == -1:
            return None

        raw_json = html[json_start + 1 : json_end]
        if not raw_json:
            return None

        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return None

    def _extract_category_data(self, payload: dict) -> Optional[dict]:
        return (
            payload.get("props", {})
            .get("pageProps", {})
            .get("initialProps", {})
            .get("categoryData")
        )

    def _map_product(self, item: dict) -> Dict:
        discount_info = item.get("discount") or {}

        new_price = self._format_cents_price(item.get("price"))
        old_price = self._format_cents_price(discount_info.get("old_price"))
        discount = (
            str(discount_info.get("value")) if discount_info.get("value") is not None else ""
        )
        if discount:
            discount = f"-{discount}%"

        image_url = self._extract_image_url(item.get("img"))
        product_url = clean_text(item.get("web_url"))
        if product_url and product_url.startswith("/"):
            product_url = f"{self.settings.metro_base_url.rstrip('/')}{product_url}"

        valid_to = clean_text(discount_info.get("due_date"))

        return {
            "source_code": self.source_code,
            "source_name": self.source_name,
            "name": clean_text(item.get("title")),
            "new_price": new_price,
            "old_price": old_price,
            "discount": discount,
            "category": clean_text(item.get("category_id")),
            "image_url": image_url,
            "product_url": product_url,
            "valid_from": "",
            "valid_to": valid_to,
        }

    def _extract_image_url(self, value) -> str:
        if isinstance(value, str):
            text = clean_text(value)
            return text if text.startswith("http") else ""

        if isinstance(value, dict):
            preferred_keys = ("s350x350", "s200x200", "s150x150", "s1350x1350")
            for key in preferred_keys:
                candidate = clean_text(value.get(key))
                if candidate.startswith("http"):
                    return candidate

            for candidate in value.values():
                url = clean_text(candidate)
                if url.startswith("http"):
                    return url

        return ""

    def _format_cents_price(self, value) -> str:
        if value is None:
            return ""
        try:
            numeric = float(value) / 100.0
            return f"{numeric:.2f}"
        except (TypeError, ValueError):
            return ""

    def _build_page_url(self, base_url: str, page_number: int) -> str:
        parsed = urlparse(base_url)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))

        query_items["page"] = str(page_number)
        new_query = urlencode(query_items)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )
