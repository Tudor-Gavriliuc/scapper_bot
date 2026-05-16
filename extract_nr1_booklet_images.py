from __future__ import annotations

import json
import re
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://nr1.md"
BOOKLETS_URL = "https://nr1.md/ro/booklets/"
OUTPUT_PATH = Path("data/nr1_booklet_images_today.json")
MAX_BOOKLET_AGE_DAYS = 14


def _extract_date_from_slug(url: str) -> Optional[date]:
    """Extract ddmmyyyy from booklet slug URL and convert it to date."""
    match = re.search(r"(\d{2})(\d{2})(\d{4})(?:$|[-/])", url)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _get_booklet_links() -> List[str]:
    response = requests.get(
        BOOKLETS_URL,
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links: List[str] = []
    seen = set()
    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(BASE_URL, href)
        if "/ro/booklets/booklet-" not in full:
            continue
        if full in seen:
            continue
        seen.add(full)
        links.append(full)

    return links


def _pick_today_booklet(links: List[str]) -> Optional[Tuple[str, Optional[date]]]:
    if not links:
        return None

    today = date.today()
    dated_links = [(link, _extract_date_from_slug(link)) for link in links]

    valid = [(link, d) for link, d in dated_links if d is not None and d <= today]
    if valid:
        valid.sort(key=lambda x: x[1], reverse=True)
        return valid[0]

    fallback = [(link, d) for link, d in dated_links if d is not None]
    if fallback:
        fallback.sort(key=lambda x: x[1], reverse=True)
        return fallback[0]

    return links[0], None


def _is_booklet_date_valid(booklet_date: Optional[date]) -> bool:
    if booklet_date is None:
        return True

    today = date.today()
    if booklet_date > today:
        return False

    age_days = (today - booklet_date).days
    return age_days <= MAX_BOOKLET_AGE_DAYS


def _get_anyflip_iframe(booklet_url: str) -> str:
    response = requests.get(
        booklet_url,
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    iframe = soup.select_one("iframe[src]")
    if not iframe:
        raise RuntimeError("No AnyFlip iframe found on booklet page")

    iframe_src = (iframe.get("src") or "").strip()
    if not iframe_src:
        raise RuntimeError("Empty AnyFlip iframe src")

    return iframe_src


def _collect_anyflip_images(anyflip_url: str) -> List[str]:
    ordered_images: "OrderedDict[str, None]" = OrderedDict()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        def on_response(response) -> None:
            url = response.url.split("?", 1)[0]
            if "/files/large/" not in url:
                return
            if not url.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
                return
            ordered_images[url] = None

        page.on("response", on_response)
        page.goto(anyflip_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Walk pages until no new image appears for several consecutive steps.
        stale_steps = 0
        last_count = 0
        max_steps = 140
        for _ in range(max_steps):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(350)
            current_count = len(ordered_images)
            if current_count == last_count:
                stale_steps += 1
            else:
                stale_steps = 0
                last_count = current_count
            if stale_steps >= 14:
                break

        browser.close()

    return list(ordered_images.keys())


def extract_today_booklet_images() -> dict:
    links = _get_booklet_links()
    selected = _pick_today_booklet(links)
    if not selected:
        raise RuntimeError("No booklet links found")

    booklet_url, booklet_date = selected
    if not _is_booklet_date_valid(booklet_date):
        raise RuntimeError(
            "Selected NR1 booklet date is not valid for today: "
            f"{booklet_date.isoformat() if booklet_date else '-'}"
        )

    anyflip_url = _get_anyflip_iframe(booklet_url)
    images = _collect_anyflip_images(anyflip_url)

    payload = {
        "source": "nr1",
        "booklet_url": booklet_url,
        "booklet_date": booklet_date.isoformat() if booklet_date else "",
        "is_valid_for_today": _is_booklet_date_valid(booklet_date),
        "anyflip_url": anyflip_url,
        "images": images,
        "image_count": len(images),
    }
    return payload


def main() -> None:
    payload = extract_today_booklet_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[INFO] Selected booklet: {payload['booklet_url']}")
    if payload["booklet_date"]:
        print(f"[INFO] Booklet date: {payload['booklet_date']}")
    print(f"[INFO] Extracted images: {payload['image_count']}")
    print(f"[INFO] Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
