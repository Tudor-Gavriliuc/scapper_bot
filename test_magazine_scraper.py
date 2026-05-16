#!/usr/bin/env python
"""Test script for magazine scraper - with mock OCR fallback."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings
from scrapers.magazine_scraper import MagazineScraper

def test_magazine_scraper_basic():
    """Test basic magazine scraper functionality."""
    print("=" * 70)
    print("MAGAZINE SCRAPER TEST")
    print("=" * 70)
    print()
    
    # Check Tesseract installation
    print("[CHECK] Tesseract OCR installation...")
    try:
        import pytesseract
        import subprocess
        try:
            result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
            print(f"[OK] Tesseract found: {result.stdout.split(chr(10))[0]}")
            tesseract_available = True
        except FileNotFoundError:
            print("[WARN] Tesseract not installed. Install it to enable OCR.")
            print("       See MAGAZINE_SETUP.md for installation instructions.")
            tesseract_available = False
    except ImportError:
        print("[ERROR] pytesseract not installed")
        tesseract_available = False
    
    print()
    
    # Check configuration
    print("[CONFIG] Magazine scraper settings:")
    print(f"  ENABLE_MAGAZINE: {settings.enable_magazine}")
    print(f"  MAGAZINE_URL: {settings.magazine_url}")
    print(f"  MAGAZINE_IMAGE_SELECTOR: {settings.magazine_image_selector}")
    print(f"  MIN_DISCOUNT_PERCENTAGE: {settings.min_discount_percentage}")
    print(f"  OCR_LANGUAGE: {settings.magazine_ocr_language}")
    print(f"  CROP: left={settings.magazine_crop_left}, top={settings.magazine_crop_top}, "
          f"right={settings.magazine_crop_right}, bottom={settings.magazine_crop_bottom}")
    print()
    
    if not settings.enable_magazine:
        print("[SKIP] Magazine scraper is disabled (ENABLE_MAGAZINE=0)")
        return
    
    # Test scraper initialization
    print("[TEST] Initializing magazine scraper...")
    try:
        scraper = MagazineScraper(settings)
        print(f"[OK] Scraper initialized")
        print(f"     Source code: {scraper.source_code}")
        print(f"     Source name: {scraper.source_name}")
        print(f"     Temp dir: {scraper.temp_dir}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize scraper: {e}")
        return
    
    print()
    
    # Test page fetching
    print("[TEST] Testing magazine page fetch...")
    try:
        html = scraper.fetch_html(settings.magazine_url)
        if html:
            print(f"[OK] Magazine page fetched ({len(html)} bytes)")
        else:
            print("[WARN] Magazine page is empty")
            return
    except Exception as e:
        print(f"[ERROR] Failed to fetch magazine page: {e}")
        return
    
    print()
    
    # Test image detection
    print("[TEST] Testing magazine image detection...")
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        images = soup.select(settings.magazine_image_selector)
        print(f"[OK] Found {len(images)} magazine images using selector: {settings.magazine_image_selector}")
        
        for i, img in enumerate(images[:3], 1):
            src = img.get('src', 'N/A')
            print(f"     Image {i}: {src[:60]}...")
    except Exception as e:
        print(f"[ERROR] Failed to detect images: {e}")
        return
    
    print()
    
    if not tesseract_available:
        print("[INFO] Skipping actual OCR processing (Tesseract not installed)")
        print("[INFO] Magazine scraper is ready to use once Tesseract is installed")
        return
    
    # Full scrape test
    print("[TEST] Running full magazine scrape (with OCR)...")
    try:
        products = scraper.scrape()
        print(f"[OK] Scraper completed")
        print(f"     Found {len(products)} products with discount >= {settings.min_discount_percentage}%")
        
        if products:
            print()
            print("[PRODUCTS]")
            for i, p in enumerate(products[:5], 1):
                print(f"\n  Product {i}:")
                print(f"    Name: {p.get('name', 'N/A')}")
                print(f"    Price: {p.get('new_price', 'N/A')} MDL (was {p.get('old_price', 'N/A')})")
                print(f"    Discount: {p.get('discount', 'N/A')}")
                print(f"    Valid: {p.get('valid_from')} to {p.get('valid_to')}")
        
    except Exception as e:
        print(f"[ERROR] Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("[DONE] Magazine scraper test completed successfully!")

if __name__ == '__main__':
    test_magazine_scraper_basic()
