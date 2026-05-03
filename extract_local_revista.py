from __future__ import annotations

import json
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mylocal.md"
REVISTA_URL = "https://mylocal.md/revista"
OUTPUT_PATH = Path("data/local_revista_images_today.json")


def extract_local_revista_images() -> dict:
    response = requests.get(
        REVISTA_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Local revista page currently exposes gallery image links directly.
    image_urls: List[str] = []
    seen = set()

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue

        full = urljoin(BASE_URL, href)
        low = full.lower()
        if "new.mylocal.md/wp-content/uploads/gallery/" not in low:
            continue
        if not low.endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        if full in seen:
            continue

        seen.add(full)
        image_urls.append(full)

    payload = {
        "source": "local",
        "revista_url": REVISTA_URL,
        "images": image_urls,
        "image_count": len(image_urls),
    }
    return payload


def main() -> None:
    payload = extract_local_revista_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[INFO] Local revista URL: {payload['revista_url']}")
    print(f"[INFO] Extracted images: {payload['image_count']}")
    print(f"[INFO] Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
