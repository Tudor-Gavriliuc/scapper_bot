from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://catalogreduceri.md"
SHOP_URL = "https://catalogreduceri.md/store/bonus"
OUTPUT_PATH = Path("data/bonus_booklet_images_today.json")


def _normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\xa0", " ").split()).strip()


def _parse_validity_range(text: str) -> Tuple[Optional[date], Optional[date]]:
    clean = _normalize_text(text).lower()

    # Example: 07.05 - 20.05.2026
    m = re.search(
        r"(\d{1,2})[./](\d{1,2})\s*-\s*(\d{1,2})[./](\d{1,2})[./](\d{4})",
        clean,
    )
    if m:
        d1, m1, d2, m2, y2 = map(int, m.groups())
        try:
            return date(y2, m1, d1), date(y2, m2, d2)
        except ValueError:
            pass

    # Example: 07.05.2026 - 20.05.2026
    m = re.search(
        r"(\d{1,2})[./](\d{1,2})[./](\d{4})\s*-\s*(\d{1,2})[./](\d{1,2})[./](\d{4})",
        clean,
    )
    if m:
        d1, m1, y1, d2, m2, y2 = map(int, m.groups())
        try:
            return date(y1, m1, d1), date(y2, m2, d2)
        except ValueError:
            pass

    return None, None


def _collect_catalog_candidates() -> List[dict]:
    # Use Playwright to bypass bot-detection (requests gets 403 on server IPs).
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(SHOP_URL, wait_until="domcontentloaded", timeout=30000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    out: List[dict] = []
    seen = set()
    for anchor in soup.select("a[href]"):
        href = _normalize_text(anchor.get("href") or "")
        if not href:
            continue

        full_href = urljoin(BASE_URL, href)
        if "/catalog/" not in full_href:
            continue
        if full_href in seen:
            continue

        seen.add(full_href)
        label = _normalize_text(anchor.get_text(" ", strip=True))
        valid_from, valid_to = _parse_validity_range(label)
        out.append(
            {
                "catalog_url": full_href,
                "label": label,
                "valid_from": valid_from,
                "valid_to": valid_to,
            }
        )

    return out


def _pick_valid_catalog(candidates: List[dict]) -> Optional[dict]:
    if not candidates:
        return None

    today = date.today()

    current = [
        c
        for c in candidates
        if c["valid_from"] and c["valid_to"] and c["valid_from"] <= today <= c["valid_to"]
    ]
    if current:
        current.sort(key=lambda c: c["valid_to"], reverse=True)
        return current[0]

    upcoming = [c for c in candidates if c["valid_from"] and c["valid_from"] > today]
    if upcoming:
        upcoming.sort(key=lambda c: c["valid_from"])
        return upcoming[0]

    with_dates = [c for c in candidates if c["valid_to"]]
    if with_dates:
        with_dates.sort(key=lambda c: c["valid_to"], reverse=True)
        return with_dates[0]

    return candidates[0]


def _extract_page_number_from_url(url: str) -> Optional[int]:
    m = re.search(r"/page_(\d{1,3})\.", (url or "").lower())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _collect_catalog_images(catalog_url: str) -> List[str]:
    response = requests.get(
        catalog_url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    def is_catalog_image_url(url: str) -> bool:
        low = (url or "").lower()
        if not low.startswith("https://catalogreduceri.md/storage/"):
            return False
        if not low.endswith((".webp", ".jpg", ".jpeg", ".png")):
            return False
        if "/conversions/" in low or "_logo" in low:
            return False
        return "/page_" in low

    by_page: dict[int, str] = {}

    # Static URLs present in HTML.
    for m in re.finditer(r"https://catalogreduceri\.md/storage/[^\"'\s>]+\.(?:webp|jpg|jpeg|png)", response.text, re.I):
        url = m.group(0)
        if not is_catalog_image_url(url):
            continue
        page_no = _extract_page_number_from_url(url)
        if page_no is not None:
            by_page.setdefault(page_no, url)

    # Dynamic URLs while navigating pages.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for _attempt in range(3):
            page = browser.new_page(viewport={"width": 1400, "height": 1000})

            def on_response(resp) -> None:
                url = resp.url.split("?", 1)[0]

                if is_catalog_image_url(url):
                    page_no = _extract_page_number_from_url(url)
                    if page_no is not None:
                        by_page.setdefault(page_no, url)
                    return

                if "livewire/update" in url:
                    try:
                        body = resp.text()
                    except Exception:
                        return

                    for m in re.finditer(
                        r"https://catalogreduceri\.md/storage/[^\"'\s>]+\.(?:webp|jpg|jpeg|png)",
                        body,
                        re.I,
                    ):
                        candidate = m.group(0)
                        if not is_catalog_image_url(candidate):
                            continue
                        page_no = _extract_page_number_from_url(candidate)
                        if page_no is not None:
                            by_page.setdefault(page_no, candidate)

            page.on("response", on_response)
            page.goto(catalog_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2200)

            # First pass to the end.
            for _ in range(220):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(170)

            # Second pass back to start to force lazy-loaded gaps.
            for _ in range(220):
                page.keyboard.press("ArrowLeft")
                page.wait_for_timeout(170)

            # Third short pass forward.
            for _ in range(120):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(150)

            page.close()

            if len(by_page) >= 16:
                break

        browser.close()

    return [by_page[k] for k in sorted(by_page)]


def extract_bonus_booklet_images() -> dict:
    candidates = _collect_catalog_candidates()
    selected = _pick_valid_catalog(candidates)
    if not selected:
        raise RuntimeError("No Bonus catalog candidates found")

    images = _collect_catalog_images(selected["catalog_url"])

    valid_from = selected.get("valid_from")
    valid_to = selected.get("valid_to")
    today = date.today()
    is_valid = bool(valid_from and valid_to and valid_from <= today <= valid_to)

    return {
        "source": "bonus",
        "shop_url": SHOP_URL,
        "catalog_url": selected["catalog_url"],
        "catalog_label": selected.get("label") or "",
        "valid_from": valid_from.isoformat() if valid_from else "",
        "valid_to": valid_to.isoformat() if valid_to else "",
        "is_valid_for_today": is_valid,
        "images": images,
        "image_count": len(images),
    }


def main() -> None:
    payload = extract_bonus_booklet_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[INFO] Selected Bonus catalog: {payload['catalog_url']}")
    print(f"[INFO] Validity: {payload.get('valid_from') or '-'} - {payload.get('valid_to') or '-'}")
    print(f"[INFO] Valid for today: {payload['is_valid_for_today']}")
    print(f"[INFO] Extracted images: {payload['image_count']}")
    print(f"[INFO] Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
