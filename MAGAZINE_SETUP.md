# Magazine Scraper Setup & Configuration

This document explains how to set up and configure the magazine scraper to extract products from mylocal.md/ro/revista using OCR.

## Prerequisites

The magazine scraper requires **Tesseract OCR** to be installed separately on your system. The Python package `pytesseract` is just a wrapper around the Tesseract engine.

### Install Tesseract OCR

#### Windows

1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
   - Latest version: `tesseract-ocr-w64-setup-v5.x.x.exe`

2. Run the installer with default settings
   - Default install location: `C:\Program Files\Tesseract-OCR`

3. Verify installation:
   ```powershell
   tesseract --version
   ```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ron
```

#### macOS

```bash
brew install tesseract
```

### Configure pytesseract Path (Windows only)

If Tesseract is installed in a non-standard location, add this to `.env`:

```
PYTESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Then update `scrapers/magazine_scraper.py`:

```python
import pytesseract
import os

if os.getenv("PYTESSERACT_PATH"):
    pytesseract.pytesseract.pytesseract_cmd = os.getenv("PYTESSERACT_PATH")
```

## Configuration

### Environment Variables (.env)

Add these settings to your `.env` file:

```
# Magazine scraper
ENABLE_MAGAZINE=1
MAGAZINE_URL=https://mylocal.md/ro/revista
MAGAZINE_IMAGE_SELECTOR=img[src*='cdn'], img[src*='revista'], [data-catalog-page]
MAGAZINE_OCR_LANGUAGE=eng+ron
MAGAZINE_CROP_LEFT=180
MAGAZINE_CROP_TOP=260
MAGAZINE_CROP_RIGHT=260
MAGAZINE_CROP_BOTTOM=130
```

### Configuration Details

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_MAGAZINE` | `1` | Enable/disable magazine scraper (0=disabled, 1=enabled) |
| `MAGAZINE_URL` | `https://mylocal.md/ro/revista` | Magazine catalog URL |
| `MAGAZINE_IMAGE_SELECTOR` | Various selectors | CSS selector to find catalog images |
| `MAGAZINE_OCR_LANGUAGE` | `eng+ron` | OCR languages (English + Romanian) |
| `MAGAZINE_CROP_LEFT` | `180` | Left offset for product crop (px) |
| `MAGAZINE_CROP_TOP` | `260` | Top offset for product crop (px) |
| `MAGAZINE_CROP_RIGHT` | `260` | Right offset for product crop (px) |
| `MAGAZINE_CROP_BOTTOM` | `130` | Bottom offset for product crop (px) |

### Adjusting Crop Dimensions

The `MAGAZINE_CROP_*` values define how much area around a detected discount is cropped as a product image. Adjust these if:

- **Crop includes too much background**: Increase offsets (e.g., `CROP_LEFT=150`)
- **Crop cuts off product**: Decrease offsets (e.g., `CROP_LEFT=200`)

First run the scraper, then inspect the cropped images in the temp directory and adjust as needed.

## How It Works

1. **Download**: Downloads magazine catalog pages (.webp/.png images) from `MAGAZINE_URL`
2. **OCR**: Runs Tesseract OCR to detect all text in the images
3. **Find Discounts**: Searches for discount percentages (e.g., "30%", "50 %")
4. **Crop**: Extracts a product region around each detected discount
5. **Extract Prices**: Uses OCR on the cropped region to find old/new prices
6. **Filter**: Only keeps products with discount >= `MIN_DISCOUNT_PERCENTAGE`
7. **Store**: Saves products to database with crop image path

## Testing

### Test Magazine Scraper Locally

Create a test script `test_magazine.py`:

```python
from core.config import settings
from scrapers.magazine_scraper import MagazineScraper

scraper = MagazineScraper(settings)
products = scraper.scrape()

print(f"Found {len(products)} products")
for p in products:
    print(f"  - {p['name']}: {p['new_price']} MDL (was {p['old_price']}), {p['discount']} off")
```

Run it:
```powershell
python test_magazine.py
```

### Inspect Cropped Images

Cropped product images are saved to a temporary directory. To keep them:

1. Modify `magazine_scraper.py` to use a persistent directory:
   ```python
   self.temp_dir = "data/magazine_crops"  # Instead of tempfile.mkdtemp()
   ```

2. Run the scraper
3. Check `data/magazine_crops/` for cropped product images

### OCR Accuracy Issues

If OCR is not detecting prices correctly:

1. Check the cropped images — are they showing the price?
2. Increase crop offsets to include more context
3. Try different `MAGAZINE_OCR_LANGUAGE` settings:
   - `eng` — English only
   - `eng+ron` — English + Romanian
   - `ron` — Romanian only

## Troubleshooting

### "tesseract is not installed" Error

```
pytesseract.TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

**Solution**: Install Tesseract following the Windows/Linux/macOS instructions above.

### No magazine images found

Check selector accuracy:
1. Visit `https://mylocal.md/ro/revista` in browser
2. Right-click on a catalog image → "Inspect"
3. Update `MAGAZINE_IMAGE_SELECTOR` in `.env` to match actual HTML structure

### Poor OCR accuracy on discounts

1. Inspect cropped images in temp directory
2. The discount % text might be too small or blurry
3. Try increasing `MAGAZINE_CROP_TOP` and `MAGAZINE_CROP_BOTTOM` to include more context

### Prices not extracted correctly

OCR may misread numbers. The regex pattern `\d+[.,]\d{1,2}` looks for patterns like:
- `29.99`
- `29,99`
- `30.5`

If prices use different formats, adjust `_parse_prices()` in `magazine_scraper.py`.

## Integration with Main Pipeline

The magazine scraper is automatically integrated:

1. Enabled via `ENABLE_MAGAZINE=1` in `.env`
2. Registered in `scrapers/scraper_registry.py`
3. Runs as part of `main.py` scrape cycle
4. Products saved with `source_code = "magazine"`
5. Posted to Telegram like any other product

Run normally:
```powershell
python main.py
```

## GitHub Actions Integration

The magazine scraper will run automatically in GitHub Actions CI/CD, but **Tesseract must be installed** on the runner.

Update `.github/workflows/daily-posting.yml`:

```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr tesseract-ocr-ron
```

Note: This is for Ubuntu runners. For Windows runners, use pre-built images that include Tesseract, or use `choco install tesseract`.

## Performance Notes

- **Memory**: OCR with large images can use significant memory. If running on CI/CD with limited RAM, consider resizing images before OCR.
- **Speed**: OCR is slower than HTML parsing. Expect 5-10 seconds per page.
- **Network**: Large .webp/.png downloads can be slow. Use timeouts appropriately.

## Future Enhancements

Potential improvements:

1. **Image preprocessing**: Enhance contrast/brightness before OCR for better accuracy
2. **Price validation**: Verify extracted prices are reasonable (e.g., >0, <10000)
3. **Product naming**: Use image context (nearby text) to generate better product names
4. **Duplicate detection**: Compare cropped images using image hashing
5. **Multilingual OCR**: Better support for language detection
