#!/usr/bin/env python
"""Test script to analyze mylocal.md/ro/revista page structure."""

import requests
from bs4 import BeautifulSoup

def test_magazine_page():
    url = 'https://mylocal.md/ro/revista'
    try:
        print("[INFO] Fetching magazine page...")
        response = requests.get(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, 
            timeout=15
        )
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print(f"[OK] Page fetched ({len(html)} bytes)")
        print()
        
        # Count images
        all_imgs = soup.select('img')
        imgs_with_src = [img for img in all_imgs if img.get('src')]
        imgs_with_data_src = [img for img in all_imgs if img.get('data-src')]
        
        print(f"[IMAGES] Total img tags: {len(all_imgs)}")
        print(f"[IMAGES] With src attribute: {len(imgs_with_src)}")
        print(f"[IMAGES] With data-src attribute: {len(imgs_with_data_src)}")
        print()
        
        # Show first few images
        print("[SAMPLE IMG TAGS]")
        for i, img in enumerate(all_imgs[:8], 1):
            src = img.get('src', '')
            data_src = img.get('data-src', '')
            alt = img.get('alt', '')
            print(f"\nImage {i}:")
            print(f"  src: {src[:70] if src else 'N/A'}")
            print(f"  data-src: {data_src[:70] if data_src else 'N/A'}")
            print(f"  alt: {alt[:50] if alt else 'N/A'}")
        
        # Find gallery/catalog images specifically
        print("\n[GALLERY IMAGES] Looking for magazine catalog pages...")
        gallery_imgs = [img for img in all_imgs if 'gallery' in img.get('src', '')]
        print(f"Found {len(gallery_imgs)} gallery images")
        for img in gallery_imgs[:5]:
            print(f"  {img.get('src')}")
        
        # Check for links to catalog images
        print("\n[LINKS] Looking for catalog/magazine links...")
        for a in soup.select('a[href*="revista"]')[:3]:
            href = a.get('href', 'N/A')
            text = a.get_text(strip=True)[:50]
            print(f"  href: {href[:70]}")
            print(f"  text: {text}")
            
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

if __name__ == '__main__':
    test_magazine_page()
