import time
from collections import defaultdict

from core.config import settings
from core.database import Database
from core.normalizer import get_product_discount_percentage, is_product_expired
from core.telegram_bot import TelegramBot
from scrapers.scraper_registry import get_scrapers


def main() -> None:
    print("[INFO] Starting promo scraper bot...")

    db = Database(settings.database_path)
    db.initialize()

    all_products = []
    scrapers = get_scrapers(settings)

    if not scrapers:
        print("[WARN] No scrapers configured.")
        return

    for scraper in scrapers:
        print(f"[INFO] Running scraper: {scraper.source_name}")
        try:
            products = scraper.scrape()
            if not products:
                print(f"[INFO] No products found for source: {scraper.source_name}")
            all_products.extend(products)
        except Exception as exc:
            print(f"[ERROR] Scraper failed for {scraper.source_name}: {exc}")

    if not all_products:
        print("[INFO] No products collected from any source.")
    else:
        print(f"[INFO] Collected products total: {len(all_products)}")

    filtered_products = []
    excluded_by_discount = 0
    excluded_by_expiry = 0
    for product in all_products:
        if is_product_expired(product):
            excluded_by_expiry += 1
            continue

        discount_pct = get_product_discount_percentage(product)
        if discount_pct is None or discount_pct <= settings.min_discount_percentage:
            excluded_by_discount += 1
            continue
        filtered_products.append(product)

    if all_products:
        print(
            "[INFO] Discount filter applied "
            f"(>{settings.min_discount_percentage}%): kept={len(filtered_products)}, "
            f"excluded={excluded_by_discount}"
        )
        if excluded_by_expiry:
            print(f"[INFO] Expiry filter applied: excluded_expired={excluded_by_expiry}")

    inserted_count = db.insert_new_products(filtered_products)
    print(f"[INFO] New products inserted: {inserted_count}")

    unposted = db.get_unposted_products()
    if unposted:
        before_unposted = len(unposted)
        unposted = [
            p
            for p in unposted
            if (get_product_discount_percentage(p) or 0) > settings.min_discount_percentage
        ]
        after_discount = len(unposted)
        unposted = [p for p in unposted if not is_product_expired(p)]
        excluded_expired_existing = after_discount - len(unposted)

        if len(unposted) != before_unposted:
            print(
                "[INFO] Filtered existing unposted products by discount "
                f"(>{settings.min_discount_percentage}%): kept={len(unposted)}, "
                f"excluded={before_unposted - len(unposted)}"
            )
        if excluded_expired_existing:
            print(
                "[INFO] Filtered existing unposted products by expiry: "
                f"excluded={excluded_expired_existing}"
            )

    if not unposted:
        print("[INFO] No unposted products found.")
        return

    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        print("[WARN] Telegram config missing. Skipping Telegram posting.")
        return

    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_channel_id)
    posted_ids = []
    max_groups = max(settings.telegram_max_posts_per_run, 1)
    items_per_group = max(settings.telegram_items_per_group, 1)
    delay_seconds = max(settings.telegram_send_delay_seconds, 0.0)

    eligible_unposted = []
    for product in unposted:
        if not product.get("name") or not product.get("new_price"):
            print(
                "[WARN] Skipping Telegram post for product with missing name/new_price: "
                f"id={product.get('id')}"
            )
            continue

        eligible_unposted.append(product)

    if not eligible_unposted:
        print("[INFO] No eligible products for Telegram posting.")
        return

    products_by_source = defaultdict(list)
    for product in eligible_unposted:
        source_code = (product.get("source_code") or "unknown").strip().lower()
        source_name = (product.get("source_name") or source_code.title()).strip()
        products_by_source[(source_code, source_name)].append(product)

    sent_groups = 0
    stop_sending = False
    for (source_code, source_name), source_products in products_by_source.items():
        for idx in range(0, len(source_products), items_per_group):
            if sent_groups >= max_groups:
                print(f"[INFO] Reached per-run group limit: {max_groups}")
                stop_sending = True
                break

            batch = source_products[idx : idx + items_per_group]
            sent = bot.send_batch_promotions(source_code, source_name, batch)
            if sent:
                posted_ids.extend([p["id"] for p in batch])
                sent_groups += 1
                print(
                    "[INFO] Telegram posted batch "
                    f"source={source_code}, items={len(batch)}"
                )
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

        if stop_sending:
            break

    if posted_ids:
        db.mark_products_as_posted(posted_ids)
        print(f"[INFO] Marked as posted: {len(posted_ids)}")
    else:
        print("[INFO] No products were posted to Telegram.")

    print("[INFO] Finished.")


if __name__ == "__main__":
    main()
