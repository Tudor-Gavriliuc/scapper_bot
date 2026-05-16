"""Magazine/Catalog scraper using OCR to extract discounted products from images."""

import os
import re
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

# Configure pytesseract path
# Check environment variable first, then try common Windows location
if os.getenv("PYTESSERACT_PATH"):
    pytesseract.pytesseract.pytesseract_cmd = os.getenv("PYTESSERACT_PATH")
elif os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'


class MagazineScraper(BaseScraper):
    source_code = "local"
    source_name = "Local"

    def __init__(self, settings):
        super().__init__(settings)
        # Save magazine images to a permanent folder
        self.image_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'magazine_images')
        os.makedirs(self.image_dir, exist_ok=True)

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

                    page_path = os.path.join(self.image_dir, f"magazine_page_{index}.png")
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
        """Process a single magazine page: OCR discounts, then post full page image."""
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
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )

            qualifying_discounts: List[int] = []
            for text in ocr_data.get("text", []):
                text = str(text).strip()
                discount = self._extract_discount_number(text)
                if discount is None:
                    continue
                if discount >= self.settings.min_discount_percentage:
                    qualifying_discounts.append(discount)

            if qualifying_discounts:
                top_discount = max(qualifying_discounts)
                product = {
                    "source_code": self.source_code,
                    "source_name": self.source_name,
                    "name": f"Pagina {page_number}",
                    # Required by DB schema/validation, discount drives filtering logic.
                    "new_price": str(top_discount),
                    "old_price": "-",
                    "discount": f"{top_discount}%",
                    "category": "Magazine Page",
                    "valid_from": datetime.now().strftime("%d.%m.%Y"),
                    "valid_to": (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y"),
                    "image_url": os.path.abspath(page_path),
                    "product_url": self.settings.magazine_url,
                }
                results.append(product)

            print(
                f"[INFO] Page {page_number}: Found {len(qualifying_discounts)} discounts "
                f">= {self.settings.min_discount_percentage}%"
            )

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

    # Legacy helpers kept for potential future OCR tuning.

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
        if not text or len(text) < 3:
            return None, None
        
        # Try multiple price patterns
        # Pattern 1: Prices with . or , as decimal separator
        prices = re.findall(r'\d{1,4}[.,]\d{1,2}', text)
        
        if not prices:
            # Pattern 2: Prices without decimals (for integer prices)
            prices = re.findall(r'\b\d{2,4}\b', text)
        
        if not prices:
            return None, None
        
        # Clean prices (replace commas with dots)
        prices = [p.replace(',', '.') for p in prices]
        
        try:
            # Convert to floats for comparison
            price_floats = []
            for p in prices:
                try:
                    price_floats.append((float(p), p))
                except ValueError:
                    continue
            
            if len(price_floats) == 0:
                return None, None
            
            # Sort by price value
            price_floats.sort(key=lambda x: x[0])
            
            # For 2+ prices, assume lowest is new, highest is old
            if len(price_floats) >= 2:
                new_price = price_floats[0][1]
                old_price = price_floats[-1][1]
                return old_price, new_price
            
            # For single price, might be new price only
            if len(price_floats) == 1:
                return None, price_floats[0][1]
        
        except (ValueError, IndexError):
            pass
        
        return None, None
