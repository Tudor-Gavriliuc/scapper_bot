"""Magazine/Catalog scraper using OCR to extract discounted products from images."""

import os
import re
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import requests
import cv2
import numpy as np
import pytesseract
from PIL import Image
from bs4 import BeautifulSoup

from core.normalizer import clean_text
from scrapers.base_scraper import BaseScraper

# Configure pytesseract path if set in environment
if os.getenv("PYTESSERACT_PATH"):
    pytesseract.pytesseract.pytesseract_cmd = os.getenv("PYTESSERACT_PATH")


class MagazineScraper(BaseScraper):
    source_code = "magazine"
    source_name = "Magazine Local"

    def __init__(self, settings):
        super().__init__(settings)
        self.temp_dir = tempfile.mkdtemp(prefix="magazine_scraper_")

    def scrape(self) -> List[Dict]:
        """Download magazine pages and extract products with discount > MIN_DISCOUNT."""
        products: List[Dict] = []

        try:
            page_paths = self._download_magazine_pages()
            if not page_paths:
                print("[WARN] No magazine pages downloaded.")
                return products

            for page_number, page_path in enumerate(page_paths, start=1):
                page_products = self._process_page(page_path, page_number)
                products.extend(page_products)

            print(f"[INFO] Magazine scraper found {len(products)} products.")

        except Exception as e:
            print(f"[ERROR] Magazine scraper failed: {e}")

        return products

    def _download_magazine_pages(self) -> List[str]:
        """Download magazine catalog images from mylocal.md/ro/revista."""
        page_paths: List[str] = []

        try:
            # Fetch the magazine page HTML
            html = self.fetch_html(self.settings.magazine_url)
            if not html:
                print("[WARN] Could not fetch magazine page HTML.")
                return page_paths

            soup = BeautifulSoup(html, "html.parser")

            # Find image links in the catalog
            # Adapt selectors based on actual mylocal.md structure
            image_links = soup.select(self.settings.magazine_image_selector)

            if not image_links:
                print(
                    "[WARN] No magazine images found. "
                    "Check selector in .env if page structure changed."
                )
                return page_paths

            print(f"[INFO] Found {len(image_links)} magazine images to download.")

            for index, link in enumerate(image_links, start=1):
                image_url = link.get("src") or link.get("data-src") or link.get("href")

                if not image_url:
                    continue

                # Handle relative URLs
                if not image_url.startswith("http"):
                    from urllib.parse import urljoin
                    image_url = urljoin(self.settings.magazine_url, image_url)

                try:
                    print(f"[INFO] Downloading magazine page {index}: {image_url}")
                    response = requests.get(
                        image_url,
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36"
                            )
                        },
                        timeout=self.settings.request_timeout_seconds,
                    )
                    response.raise_for_status()

                    page_path = os.path.join(self.temp_dir, f"magazine_page_{index}.png")
                    with open(page_path, "wb") as f:
                        f.write(response.content)

                    page_paths.append(page_path)

                except requests.RequestException as e:
                    print(f"[WARN] Failed to download magazine page {index}: {e}")
                    continue

        except Exception as e:
            print(f"[ERROR] Error downloading magazine pages: {e}")

        return page_paths

    def _process_page(self, page_path: str, page_number: int) -> List[Dict]:
        """Process a single magazine page: OCR → find discounts → crop → extract data."""
        results: List[Dict] = []

        try:
            image = cv2.imread(page_path)
            if image is None:
                print(f"[WARN] Could not load image: {page_path}")
                return results

            # Run OCR to detect all text and their positions
            ocr_data = pytesseract.image_to_data(
                Image.open(page_path),
                lang=self.settings.magazine_ocr_language,
                output_type=pytesseract.Output.DATAFRAME,
                config="--psm 6",
            )

            # Find discount percentages in OCR results
            for _, row in ocr_data.iterrows():
                text = str(row.get("text", "")).strip()
                discount = self._extract_discount_number(text)

                if discount is None or discount < self.settings.min_discount_percentage:
                    continue

                x = int(row["left"])
                y = int(row["top"])
                w = int(row["width"])
                h = int(row["height"])

                # Crop the product region around the discount text
                crop = self._crop_safe(
                    image,
                    x - self.settings.magazine_crop_left,
                    y - self.settings.magazine_crop_top,
                    x + self.settings.magazine_crop_right,
                    y + self.settings.magazine_crop_bottom,
                )

                if crop is None or crop.size == 0:
                    continue

                # Save crop image
                crop_filename = f"magazine_page_{page_number}_discount_{discount}_{x}_{y}.png"
                crop_path = os.path.join(self.temp_dir, crop_filename)
                cv2.imwrite(crop_path, crop)

                # OCR the cropped product region to extract prices
                crop_text = pytesseract.image_to_string(
                    Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                    lang=self.settings.magazine_ocr_language,
                    config="--psm 6",
                )

                old_price, new_price = self._parse_prices(crop_text)

                # Create product entry
                product = {
                    "name": f"Magazine Product P{page_number} D{discount}",
                    "old_price": old_price if old_price else "",
                    "new_price": new_price if new_price else "",
                    "discount": f"{discount}%",
                    "category": "Magazine Offer",
                    "valid_from": datetime.now().strftime("%d.%m.%Y"),
                    "valid_to": (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y"),
                    "image_url": crop_path,
                    "link": self.settings.magazine_url,
                }

                results.append(product)

            print(f"[INFO] Page {page_number}: Found {len(results)} products with discount >= {self.settings.min_discount_percentage}%")

        except Exception as e:
            print(f"[ERROR] Error processing magazine page {page_number}: {e}")

        return results

    @staticmethod
    def _extract_discount_number(text: str) -> Optional[int]:
        """Extract discount percentage from OCR text (e.g., '30 %' -> 30)."""
        text = text.replace(" ", "")
        match = re.search(r"(\d{1,3})\s*%", text)

        if match:
            try:
                discount = int(match.group(1))
                if 0 <= discount <= 100:
                    return discount
            except ValueError:
                pass

        return None

    @staticmethod
    def _crop_safe(
        image: np.ndarray, x1: int, y1: int, x2: int, y2: int
    ) -> Optional[np.ndarray]:
        """Safely crop image within bounds."""
        if image is None:
            return None

        h, w = image.shape[:2]

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if x1 >= x2 or y1 >= y2:
            return None

        return image[y1:y2, x1:x2]

    @staticmethod
    def _parse_prices(text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract old_price and new_price from OCR text using regex."""
        # Find all numbers that look like prices (can have . or ,)
        prices = re.findall(r"\d+[.,]\d{1,2}", text)
        prices = [p.replace(",", ".") for p in prices]

        old_price = None
        new_price = None

        if len(prices) >= 2:
            # Typically first price is new (lower), second is old (higher)
            # But OCR order may vary - we assume higher price is old
            try:
                price_floats = [float(p) for p in prices[:2]]
                if price_floats[0] < price_floats[1]:
                    new_price = prices[0]
                    old_price = prices[1]
                else:
                    new_price = prices[1]
                    old_price = prices[0]
            except (ValueError, IndexError):
                if len(prices) >= 1:
                    new_price = prices[0]
                if len(prices) >= 2:
                    old_price = prices[1]

        return old_price, new_price
