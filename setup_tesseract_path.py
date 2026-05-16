#!/usr/bin/env python
"""Setup script - Add Tesseract to Windows PATH permanently."""

import os
import subprocess
import sys
import winreg

def add_to_path():
    """Add Tesseract to Windows PATH."""
    tesseract_path = r'C:\Program Files\Tesseract-OCR'
    
    if not os.path.exists(tesseract_path):
        print("[SKIP] Tesseract not found at:", tesseract_path)
        return False
    
    print("[INFO] Adding Tesseract to Windows PATH...")
    
    try:
        # Open registry
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                            r'Environment', 0, winreg.KEY_ALL_ACCESS)
        
        try:
            # Read current PATH
            path, _ = winreg.QueryValueEx(key, 'Path')
        except WindowsError:
            path = ''
        
        # Check if Tesseract already in PATH
        if tesseract_path.lower() in path.lower():
            print("[OK] Tesseract already in PATH")
            return True
        
        # Add Tesseract to PATH
        if path and not path.endswith(';'):
            path += ';'
        path += tesseract_path
        
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, path)
        winreg.CloseKey(key)
        
        print("[OK] Tesseract added to PATH")
        print("[INFO] Please restart your terminal for changes to take effect")
        return True
        
    except PermissionError:
        print("[ERROR] Permission denied - need admin rights")
        print("[INFO] Trying alternative: Add to PowerShell profile...")
        return add_to_powershell_profile()
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def add_to_powershell_profile():
    """Add Tesseract to PowerShell profile."""
    tesseract_path = r'C:\Program Files\Tesseract-OCR'
    
    profile_path = os.path.expandvars(r'%USERPROFILE%\Documents\PowerShell\profile.ps1')
    profile_dir = os.path.dirname(profile_path)
    
    # Create directory if needed
    os.makedirs(profile_dir, exist_ok=True)
    
    # Add to profile
    line_to_add = f'$env:PATH = "$env:PATH;{tesseract_path}"\n'
    
    try:
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                content = f.read()
            
            if line_to_add.strip() in content:
                print("[OK] Tesseract already in PowerShell profile")
                return True
        
        with open(profile_path, 'a') as f:
            f.write(f"\n# Add Tesseract OCR to PATH\n{line_to_add}")
        
        print("[OK] Tesseract added to PowerShell profile")
        print(f"     Profile: {profile_path}")
        print("[INFO] Restart PowerShell for changes to take effect")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("TESSERACT PATH SETUP")
    print("=" * 70)
    print()
    
    success = add_to_path()
    
    if success:
        print("\n[OK] Setup complete!")
        print("\nYou can now use pytesseract:")
        print("  python main.py     # Magazine OCR will work")
    else:
        print("\n[WARN] Could not modify PATH automatically")
        print("\nManual fix (temporary):")
        print('  $env:PATH = "$env:PATH;C:\\Program Files\\Tesseract-OCR"')
        print("\nManual fix (permanent):")
        print("  1. Open Settings → Environment variables")
        print("  2. Edit 'Path' → Add: C:\\Program Files\\Tesseract-OCR")
        print("  3. Restart PowerShell")
    
    sys.exit(0 if success else 1)
