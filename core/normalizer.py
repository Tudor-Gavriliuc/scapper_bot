import hashlib
import re
from datetime import date, datetime
from typing import Any


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_price(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""

    text = text.replace(",", ".")
    text = re.sub(r"[^0-9.]", "", text)

    if text.count(".") > 1:
        first = text.find(".")
        text = text[: first + 1] + text[first + 1 :].replace(".", "")

    return text


def build_unique_key(source_code: str, name: str, new_price: str) -> str:
    raw = "|".join(
        [
            clean_text(source_code).lower(),
            clean_text(name).lower(),
            clean_text(new_price),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_discount_percentage(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None

    match = re.search(r"-?\d+(?:[\.,]\d+)?", text)
    if not match:
        return None

    try:
        return abs(float(match.group(0).replace(",", ".")))
    except ValueError:
        return None


def get_product_discount_percentage(product: dict) -> float | None:
    # First try explicit discount text from source.
    direct_discount = parse_discount_percentage(product.get("discount"))
    if direct_discount is not None:
        return direct_discount

    # If discount is missing, estimate from old/new prices when available.
    old_price_raw = normalize_price(product.get("old_price"))
    new_price_raw = normalize_price(product.get("new_price"))
    if not old_price_raw or not new_price_raw:
        return None

    try:
        old_price = float(old_price_raw)
        new_price = float(new_price_raw)
    except ValueError:
        return None

    if old_price <= 0 or new_price <= 0 or new_price >= old_price:
        return None

    return round(((old_price - new_price) / old_price) * 100, 2)


def parse_promotion_date(value: Any) -> date | None:
    text = clean_text(value)
    if not text:
        return None

    # Accept common source formats: dd.mm.yyyy, yyyy-mm-dd, dd/mm/yyyy.
    formats = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    # If value contains a range like "01.05.2026 - 07.05.2026", use the end date.
    range_match = re.search(
        r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*[-–]\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
        text,
    )
    if range_match:
        end_text = range_match.group(2).replace("/", ".")
        try:
            return datetime.strptime(end_text, "%d.%m.%Y").date()
        except ValueError:
            return None

    return None


def is_product_expired(product: dict, today: date | None = None) -> bool:
    valid_to = parse_promotion_date(product.get("valid_to"))
    if valid_to is None:
        return False

    if today is None:
        today = date.today()

    return valid_to < today
