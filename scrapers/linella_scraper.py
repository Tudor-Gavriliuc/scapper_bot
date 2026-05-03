from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core.normalizer import clean_text
from scrapers.base_scraper import BaseScraper


class LinellaScraper(BaseScraper):
    source_code = "linella"
    source_name = "Linella"

    def scrape(self) -> List[Dict]:
        entry_html = self.fetch_html(self.settings.linella_promotions_url)
        if not entry_html:
            print("[WARN] Linella promotions page HTML is empty.")
            return []

        promo_urls = self._extract_promotion_urls(entry_html)
        if not promo_urls:
            print("[INFO] No Linella promotion URLs found.")
            return []

        all_products: List[Dict] = []
        for promo_url in promo_urls:
            products = self._scrape_promotion_page(promo_url)
            all_products.extend(products)

        print(f"[INFO] Linella scraped products: {len(all_products)}")
        return all_products

    def _extract_promotion_urls(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select(self.settings.linella_promo_link_selector)

        promo_urls: List[str] = []
        seen = set()
        for link in links:
            href = clean_text(link.get("href"))
            if not href:
                continue

            full_url = urljoin(self.settings.linella_base_url, href)
            if "/ro/promotii/" not in full_url:
                continue
            if full_url.rstrip("/").endswith("/ro/promotii"):
                continue
            if full_url in seen:
                continue

            seen.add(full_url)
            promo_urls.append(full_url)

        if not promo_urls:
            # Fallback to known default promotion page.
            promo_urls = [urljoin(self.settings.linella_base_url, "/ro/promotii/mega_oferta")]

        return promo_urls

    def _scrape_promotion_page(self, promo_url: str) -> List[Dict]:
        html = self.fetch_html(promo_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.settings.linella_product_card_selector)
        if not cards:
            print(f"[INFO] No Linella product cards found at: {promo_url}")
            return []

        products: List[Dict] = []
        for card in cards:
            name = self._get_text(card, self.settings.linella_name_selector)
            new_price = self._get_text(card, self.settings.linella_new_price_selector)
            old_price = self._get_text(card, self.settings.linella_old_price_selector)
            discount = self._get_text(card, self.settings.linella_discount_selector)

            image_url = ""
            image_tag = card.select_one(self.settings.linella_image_selector)
            if image_tag:
                image_url = clean_text(
                    image_tag.get("src")
                    or image_tag.get("data-src")
                    or image_tag.get("srcset")
                )
                if image_url:
                    image_url = urljoin(self.settings.linella_base_url, image_url)

            product_url = ""
            link_tag = card.select_one(self.settings.linella_link_selector)
            if link_tag:
                href = clean_text(link_tag.get("href"))
                if href:
                    product_url = urljoin(self.settings.linella_base_url, href)

            products.append(
                {
                    "source_code": self.source_code,
                    "source_name": self.source_name,
                    "name": name,
                    "new_price": new_price,
                    "old_price": old_price,
                    "discount": discount,
                    "category": "",
                    "image_url": image_url,
                    "product_url": product_url,
                    "valid_from": "",
                    "valid_to": "",
                }
            )

        return products

    def _get_text(self, element, selector: str) -> str:
        node = element.select_one(selector)
        return clean_text(node.get_text(" ", strip=True) if node else "")
