#!/usr/bin/env python
"""Test magazine extraction without Tesseract - analyze images directly."""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings
from scrapers.magazine_scraper import MagazineScraper
import cv2
from PIL import Image

def test_magazine_extraction():
    """Test magazine image download and analysis."""
    print("=" * 70)
    print("MAGAZINE SCRAPER - IMAGE EXTRACTION TEST")
    print("=" * 70)
    print()
    
    # Initialize scraper
    scraper = MagazineScraper(settings)
    
    print("[1] DOWNLOADING MAGAZINE PAGES")
    print("-" * 70)
    
    # Download pages
    page_paths = scraper._download_magazine_pages()
    
    if not page_paths:
        print("[ERROR] No pages downloaded")
        return
    
    print(f"[OK] Downloaded {len(page_paths)} magazine pages")
    for i, path in enumerate(page_paths, 1):
        size = os.path.getsize(path) / 1024 / 1024
        print(f"     Page {i}: {path} ({size:.2f} MB)")
    
    print()
    print("[2] ANALYZING IMAGE CONTENT")
    print("-" * 70)
    
    for i, page_path in enumerate(page_paths, 1):
        print(f"\nPage {i}: {Path(page_path).name}")
        print("-" * 70)
        
        # Load image
        image = cv2.imread(page_path)
        if image is None:
            print(f"  [ERROR] Could not load image")
            continue
        
        h, w = image.shape[:2]
        print(f"  Dimensions: {w}x{h} pixels")
        print(f"  File size: {os.path.getsize(page_path) / 1024 / 1024:.2f} MB")
        
        # Convert to grayscale and analyze
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try to detect edges (product boundaries)
        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"  Detected contours: {len(contours)} (potential product areas)")
        
        # Show image info
        print(f"  Channels: BGR (color image)")
        print(f"  Mean pixel intensity: {gray.mean():.1f}")
        
        # Try to detect text regions (areas with high contrast)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        text_regions = cv2.countNonZero(binary)
        print(f"  Text-like regions: ~{text_regions // 1000}k pixels (potential discount text)")
        
        print()
        print("  [NOTE] Without Tesseract OCR, cannot extract:")
        print("    - Discount percentages")
        print("    - Price text")
        print("    - Product names")
        print()
        print("  ✓ What we CAN do:")
        print("    - Detect images are valid and loadable")
        print("    - Estimate product regions by contour detection")
        print("    - Identify text-rich areas (where discounts should be)")
    
    print()
    print("[3] EXTRACTION CAPABILITIES")
    print("-" * 70)
    print()
    print("Magazine Scraper is READY for OCR extraction.")
    print()
    print("To enable full product extraction, install Tesseract OCR:")
    print()
    print("  Windows:")
    print("    1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    print("    2. Run: tesseract-ocr-w64-setup-5.x.x.exe")
    print("    3. Verify: tesseract --version")
    print()
    print("  Once installed, run:")
    print("    python main.py")
    print()
    print("  This will extract all products with discount >= 30%")
    print()

if __name__ == '__main__':
    test_magazine_extraction()
