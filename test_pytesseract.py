#!/usr/bin/env python
"""Test pytesseract with Tesseract path."""

import pytesseract
import os
from PIL import Image, ImageDraw

# Set path
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
print(f'[CHECK] Tesseract exists: {os.path.exists(tesseract_path)}')

pytesseract.pytesseract.pytesseract_cmd = tesseract_path
print(f'[SET] pytesseract_cmd = {pytesseract.pytesseract.pytesseract_cmd}')

# Test with a simple image
try:
    # Create a test image with text
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), '30%', fill='black')
    
    text = pytesseract.image_to_string(img)
    print(f'[OK] OCR Test successful: "{text.strip()}"')
except Exception as e:
    print(f'[ERROR] OCR Test failed: {e}')
    import traceback
    traceback.print_exc()

# Test with actual magazine page
print("\n[TEST] OCR on actual magazine page...")
try:
    from core.config import settings
    from scrapers.magazine_scraper import MagazineScraper
    
    # Make sure pytesseract path is set
    if not pytesseract.pytesseract.pytesseract_cmd:
        pytesseract.pytesseract.pytesseract_cmd = tesseract_path
    
    scraper = MagazineScraper(settings)
    products = scraper.scrape()
    
    print(f'[OK] Magazine scraper found {len(products)} products')
    if products:
        for i, p in enumerate(products[:3], 1):
            print(f"  {i}. {p['name']}: {p['new_price']} MDL ({p['discount']} off)")
    
except Exception as e:
    print(f'[ERROR] Magazine scraper failed: {e}')
    import traceback
    traceback.print_exc()
