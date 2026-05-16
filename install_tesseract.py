#!/usr/bin/env python
"""Install Tesseract OCR on Windows."""

import requests
import subprocess
import os
import time
import sys

def get_latest_tesseract_url():
    """Find latest Tesseract release with w64 installer."""
    print("[INFO] Checking available Tesseract releases...")
    try:
        response = requests.get(
            'https://api.github.com/repos/UB-Mannheim/tesseract/releases?per_page=20',
            timeout=10
        )
        response.raise_for_status()
        releases = response.json()
        
        for release in releases:
            print(f"  Checking {release['tag_name']}...")
            for asset in release.get('assets', []):
                if 'w64-setup' in asset['name'] and asset['name'].endswith('.exe'):
                    url = asset['browser_download_url']
                    print(f"  [OK] Found: {asset['name']}")
                    return url
        
        print("[ERROR] No suitable Tesseract installer found")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to check releases: {e}")
        return None

def install_tesseract(url):
    """Download and install Tesseract."""
    if not url:
        print("[SKIP] No URL provided")
        return False
    
    output = os.path.expandvars(r'%TEMP%\tesseract-installer.exe')
    
    print(f"[INFO] Downloading from {url[:60]}...")
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        total = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = (downloaded / total) * 100
                    print(f"  {pct:.1f}%", end='\r')
        
        print(f"\n[OK] Downloaded {downloaded/1024/1024:.1f} MB")
        
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return False
    
    print("[INFO] Running installer (silent mode)...")
    try:
        result = subprocess.run([output, '/S'], timeout=300, check=False)
        time.sleep(2)
        print("[OK] Installation complete")
    except Exception as e:
        print(f"[ERROR] Installation failed: {e}")
        return False
    
    # Verify installation
    print("[INFO] Verifying Tesseract installation...")
    try:
        result = subprocess.run(
            [r'C:\Program Files\Tesseract-OCR\tesseract.exe', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"[OK] Tesseract installed successfully!")
            print(f"     {version_line}")
            return True
        else:
            print("[WARN] Tesseract installed but verification failed")
            return False
    except Exception as e:
        print(f"[ERROR] Could not verify: {e}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("TESSERACT OCR INSTALLER")
    print("=" * 70)
    print()
    
    url = get_latest_tesseract_url()
    if url:
        success = install_tesseract(url)
        sys.exit(0 if success else 1)
    else:
        print("\n[ERROR] Could not find Tesseract installer")
        sys.exit(1)
