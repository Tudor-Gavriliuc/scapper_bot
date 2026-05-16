import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "data/promotions.db")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")
    telegram_send_delay_seconds: float = float(
        os.getenv("TELEGRAM_SEND_DELAY_SECONDS", "1.1")
    )
    telegram_max_posts_per_run: int = int(os.getenv("TELEGRAM_MAX_POSTS_PER_RUN", "20"))
    telegram_items_per_group: int = int(os.getenv("TELEGRAM_ITEMS_PER_GROUP", "4"))

    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))
    use_playwright: bool = _as_bool(os.getenv("USE_PLAYWRIGHT", "0"))
    min_discount_percentage: float = float(os.getenv("MIN_DISCOUNT_PERCENTAGE", "30"))

    kaufland_url: str = os.getenv(
        "KAUFLAND_URL",
        "https://www.kaufland.md/ro/oferte/prezentare-generala-oferte.html",
    )
    kaufland_base_url: str = os.getenv("KAUFLAND_BASE_URL", "https://www.kaufland.md")
    kaufland_product_card_selector: str = os.getenv(
        "KAUFLAND_PRODUCT_CARD_SELECTOR",
        ".k-product-tile, article, .offer-card, .m-offer-tile",
    )
    kaufland_name_selector: str = os.getenv(
        "KAUFLAND_NAME_SELECTOR",
        ".k-product-tile__title, .m-offer-tile__title, .offer-card__title, .product-title",
    )
    kaufland_new_price_selector: str = os.getenv(
        "KAUFLAND_NEW_PRICE_SELECTOR",
        ".k-price-tag__price, .m-offer-tile__price, .offer-card__price, .new-price",
    )
    kaufland_old_price_selector: str = os.getenv(
        "KAUFLAND_OLD_PRICE_SELECTOR",
        ".k-price-tag__old-price, .m-offer-tile__old-price, .offer-card__old-price, .old-price",
    )
    kaufland_discount_selector: str = os.getenv(
        "KAUFLAND_DISCOUNT_SELECTOR",
        ".k-price-tag__discount, .m-offer-tile__discount, .offer-card__discount, .discount",
    )
    kaufland_category_selector: str = os.getenv(
        "KAUFLAND_CATEGORY_SELECTOR",
        ".k-product-tile__subtitle, .m-offer-tile__category, .offer-card__category, .category",
    )
    kaufland_image_selector: str = os.getenv(
        "KAUFLAND_IMAGE_SELECTOR",
        "img",
    )
    kaufland_link_selector: str = os.getenv(
        "KAUFLAND_LINK_SELECTOR",
        "a",
    )
    kaufland_valid_from_selector: str = os.getenv(
        "KAUFLAND_VALID_FROM_SELECTOR",
        ".valid-from, .offer-valid-from",
    )
    kaufland_valid_to_selector: str = os.getenv(
        "KAUFLAND_VALID_TO_SELECTOR",
        ".valid-to, .offer-valid-to",
    )

    enable_linella: bool = _as_bool(os.getenv("ENABLE_LINELLA", "1"))
    linella_promotions_url: str = os.getenv(
        "LINELLA_PROMOTIONS_URL",
        "https://linella.md/ro/promotii",
    )
    linella_base_url: str = os.getenv("LINELLA_BASE_URL", "https://linella.md")
    linella_promo_link_selector: str = os.getenv(
        "LINELLA_PROMO_LINK_SELECTOR",
        "a[href*='/ro/promotii/']",
    )
    linella_product_card_selector: str = os.getenv(
        "LINELLA_PRODUCT_CARD_SELECTOR",
        ".products-catalog-content__item",
    )
    linella_name_selector: str = os.getenv(
        "LINELLA_NAME_SELECTOR",
        ".products-catalog-content__name",
    )
    linella_new_price_selector: str = os.getenv(
        "LINELLA_NEW_PRICE_SELECTOR",
        ".price-products-catalog-content__new",
    )
    linella_old_price_selector: str = os.getenv(
        "LINELLA_OLD_PRICE_SELECTOR",
        ".price-products-catalog-content__old",
    )
    linella_discount_selector: str = os.getenv(
        "LINELLA_DISCOUNT_SELECTOR",
        ".price-products-catalog-content__discount",
    )
    linella_image_selector: str = os.getenv(
        "LINELLA_IMAGE_SELECTOR",
        "img",
    )
    linella_link_selector: str = os.getenv(
        "LINELLA_LINK_SELECTOR",
        "a[href]",
    )

    # Magazine scraper settings
    enable_magazine: bool = _as_bool(os.getenv("ENABLE_MAGAZINE", "1"))
    magazine_url: str = os.getenv(
        "MAGAZINE_URL",
        "https://mylocal.md/ro/revista",
    )
    magazine_image_selector: str = os.getenv(
        "MAGAZINE_IMAGE_SELECTOR",
        "img[src*='gallery']",
    )
    magazine_ocr_language: str = os.getenv("MAGAZINE_OCR_LANGUAGE", "eng+ron")
    magazine_crop_left: int = int(os.getenv("MAGAZINE_CROP_LEFT", "180"))
    magazine_crop_top: int = int(os.getenv("MAGAZINE_CROP_TOP", "260"))
    magazine_crop_right: int = int(os.getenv("MAGAZINE_CROP_RIGHT", "260"))
    magazine_crop_bottom: int = int(os.getenv("MAGAZINE_CROP_BOTTOM", "130"))


settings = Settings()
