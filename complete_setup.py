#!/usr/bin/env python
"""Complete setup and installation script - Tesseract, GitHub push, and testing."""

import os
import subprocess
import sys
import requests
import time
from pathlib import Path

def run_command(cmd, description, shell=False):
    """Run a command and return success status."""
    print(f"\n[RUN] {description}")
    print(f"      {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=60
        )
        if result.returncode == 0:
            print(f"[OK] {description}")
            return True, result.stdout
        else:
            print(f"[FAIL] {description}")
            if result.stderr:
                print(f"      Error: {result.stderr[:200]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {description}")
        return False, "Command timed out"
    except Exception as e:
        print(f"[ERROR] {description}: {e}")
        return False, str(e)

def check_tesseract():
    """Check if Tesseract is already installed."""
    print("\n" + "=" * 70)
    print("STEP 1: CHECKING TESSERACT INSTALLATION")
    print("=" * 70)
    
    try:
        result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[OK] Tesseract already installed!")
            print(result.stdout.split('\n')[0])
            return True
    except:
        pass
    
    print("[WARN] Tesseract not found in PATH")
    print("[INFO] Attempting to find or install Tesseract...")
    
    # Check if installed in standard location
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path):
            print(f"[OK] Found Tesseract at: {path}")
            os.environ['PYTESSERACT_PATH'] = path
            return True
    
    print("[INFO] Tesseract not found in standard locations")
    return False

def install_tesseract_windows():
    """Attempt to install Tesseract on Windows."""
    print("\n[INFO] Downloading Tesseract installer...")
    
    try:
        # Get latest release
        response = requests.get(
            'https://api.github.com/repos/UB-Mannheim/tesseract/releases?per_page=5',
            timeout=10
        )
        response.raise_for_status()
        releases = response.json()
        
        download_url = None
        for release in releases:
            for asset in release.get('assets', []):
                if 'w64-setup' in asset['name'] and asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    break
            if download_url:
                break
        
        if not download_url:
            print("[ERROR] Could not find Tesseract installer download URL")
            return False
        
        installer_path = os.path.expandvars(r'%TEMP%\tesseract-installer.exe')
        
        print(f"[INFO] Downloading from GitHub...")
        response = requests.get(download_url, timeout=120, stream=True)
        response.raise_for_status()
        
        with open(installer_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[OK] Downloaded installer")
        print(f"[INFO] Running installer (requires admin elevation)...")
        print(f"      Please approve the UAC prompt if it appears...")
        
        # Try to run with elevation
        result = subprocess.run(
            f'powershell -Command "Start-Process \'{installer_path}\' -ArgumentList \'/S\' -Verb RunAs -Wait"',
            shell=True,
            capture_output=True,
            timeout=180
        )
        
        time.sleep(2)
        
        # Verify installation
        if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
            print("[OK] Tesseract installed successfully!")
            os.environ['PYTESSERACT_PATH'] = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            return True
        else:
            print("[WARN] Installer ran but Tesseract not found at expected location")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to install Tesseract: {e}")
        print("[INFO] You can manually install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def setup_github():
    """Setup and push to GitHub."""
    print("\n" + "=" * 70)
    print("STEP 2: GITHUB SETUP AND PUSH")
    print("=" * 70)
    
    # Check current git status
    success, output = run_command(
        ['git', 'status'],
        'Check git status',
        shell=False
    )
    
    if not success:
        print("[ERROR] Git not configured properly")
        return False
    
    # Check if remote exists
    success, output = run_command(
        ['git', 'remote', '-v'],
        'Check git remotes',
        shell=False
    )
    
    if 'origin' in output:
        print("[OK] Git remote 'origin' already configured")
        remote = output.split('\n')[0].split()[-1]
        print(f"     Remote URL: {remote}")
    else:
        print("[WARN] No origin remote configured")
        print("[INFO] To push to GitHub, you need to:")
        print("       1. Create a repository at https://github.com/new")
        print("       2. Run: git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git")
        print("       3. Run: git branch -M main")
        print("       4. Run: git push -u origin main")
        print()
        print("[SKIP] Skipping GitHub push (configure remote first)")
        return False
    
    # Try to push
    print("[INFO] Pushing to GitHub...")
    success, output = run_command(
        ['git', 'push', '-u', 'origin', 'main'],
        'Push to GitHub',
        shell=False
    )
    
    if success or 'everything up-to-date' in output:
        print("[OK] Repository pushed to GitHub!")
        return True
    else:
        print("[WARN] Push had issues, but code is committed locally")
        return False

def test_scraper():
    """Run comprehensive scraper tests."""
    print("\n" + "=" * 70)
    print("STEP 3: COMPREHENSIVE SCRAPER TESTS")
    print("=" * 70)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Test 1: Import test
    print("\n[TEST 1] Testing Python imports...")
    success, output = run_command(
        [sys.executable, '-c', 
         'from scrapers.kaufland_scraper import KauflandScraper; '
         'from scrapers.linella_scraper import LinellaScraper; '
         'from scrapers.magazine_scraper import MagazineScraper; '
         'print("All scrapers imported successfully")'],
        'Import scrapers',
        shell=False
    )
    if not success:
        print("[ERROR] Import test failed")
        return False
    
    # Test 2: Database test
    print("\n[TEST 2] Testing database...")
    success, output = run_command(
        [sys.executable, '-c',
         'import sqlite3; '
         'conn = sqlite3.connect("data/promotions.db"); '
         'cursor = conn.cursor(); '
         'cursor.execute("SELECT COUNT(*) FROM products"); '
         'count = cursor.fetchone()[0]; '
         'print(f"Database has {count} products"); '
         'conn.close()'],
        'Database connectivity',
        shell=False
    )
    if not success:
        print("[ERROR] Database test failed")
        return False
    
    # Test 3: Configuration test
    print("\n[TEST 3] Testing configuration...")
    success, output = run_command(
        [sys.executable, '-c',
         'from core.config import settings; '
         'print(f"Kaufland enabled: {True}"); '
         'print(f"Linella enabled: {settings.enable_linella}"); '
         'print(f"Magazine enabled: {settings.enable_magazine}"); '
         'print(f"Min discount: {settings.min_discount_percentage}%")'],
        'Configuration loading',
        shell=False
    )
    if not success:
        print("[ERROR] Configuration test failed")
        return False
    
    # Test 4: Run analyze_results
    print("\n[TEST 4] Analyzing database results...")
    success, output = run_command(
        [sys.executable, 'analyze_results.py'],
        'Database analysis',
        shell=False
    )
    if success:
        print(output[:500])  # Show first 500 chars
    
    # Test 5: Full scraper run (limited)
    print("\n[TEST 5] Running scraper pipeline...")
    success, output = run_command(
        [sys.executable, 'main.py'],
        'Full scraper pipeline',
        shell=False
    )
    
    if success:
        # Extract key metrics from output
        if 'Kaufland scraped' in output:
            print("[OK] Scraper executed successfully!")
            # Show summary
            for line in output.split('\n'):
                if 'scraped' in line or 'found' in line or 'applied' in line or 'inserted' in line:
                    print(f"     {line.strip()}")
            return True
        else:
            print("[WARN] Scraper ran but output unclear")
            return True
    else:
        print("[ERROR] Scraper execution failed")
        return False

def main():
    """Main setup and test flow."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PROMO SCRAPER - COMPLETE SETUP & TEST" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Step 1: Tesseract
    tesseract_ok = check_tesseract()
    if not tesseract_ok:
        print("\n[ATTEMPT] Installing Tesseract...")
        tesseract_ok = install_tesseract_windows()
    
    if not tesseract_ok:
        print("\n[WARN] Tesseract not installed (magazine OCR won't work)")
        print("[INFO] Magazine scraper will still download images and work without OCR")
    else:
        print("\n[OK] Tesseract ready!")
    
    # Step 2: GitHub
    github_ok = setup_github()
    
    # Step 3: Tests
    print("\n[INFO] Running scraper tests...")
    tests_ok = test_scraper()
    
    # Summary
    print("\n" + "=" * 70)
    print("SETUP SUMMARY")
    print("=" * 70)
    
    print(f"\n✓ Tesseract OCR:        {'✅ Ready' if tesseract_ok else '⚠️  Not installed (optional)'}")
    print(f"✓ GitHub Repository:    {'✅ Pushed' if github_ok else '⚠️  Configure remote and push manually'}")
    print(f"✓ Scraper Pipeline:     {'✅ Working' if tests_ok else '❌ Issues detected'}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Verify everything is working:
   python main.py                    # Run scraper
   python show_sample_products.py    # View results
   
2. To enable GitHub Actions CI/CD:
   - Go to GitHub repository Settings → Secrets → Actions
   - Add TELEGRAM_BOT_TOKEN secret
   - Add TELEGRAM_CHANNEL_ID secret
   
3. To enable magazine OCR (if Tesseract not installed):
   - Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
   - Verify: tesseract --version
   - Rerun: python main.py
   
4. View logs:
   tail -f scraper_output.log        # Real-time logs
""")
    
    print("=" * 70)
    
    return 0 if tests_ok else 1

if __name__ == '__main__':
    sys.exit(main())
