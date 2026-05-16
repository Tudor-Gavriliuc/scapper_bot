from __future__ import annotations

import json

from core.config import settings
from core.revista_state import mark_posted, was_posted
from core.telegram_bot import TelegramBot
from extract_bonus_booklet_images import OUTPUT_PATH, extract_bonus_booklet_images


def main() -> None:
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        print("[WARN] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID.")
        return

    payload = extract_bonus_booklet_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_channel_id)

    catalog_url = payload.get("catalog_url") or ""
    valid_from = payload.get("valid_from") or "-"
    valid_to = payload.get("valid_to") or "-"
    images = payload.get("images") or []
    image_urls = [str(u).strip() for u in images if str(u).strip()]
    is_valid = bool(payload.get("is_valid_for_today", False))

    if not is_valid:
        print(f"[WARN] Bonus catalog not valid for today, skipping: {catalog_url}")
        return

    if was_posted("bonus", catalog_url):
        print(f"[INFO] Bonus already posted, skipping duplicate: {catalog_url}")
        return

    if not image_urls:
        print(f"[WARN] Bonus catalog has no page images, skipping: {catalog_url}")
        return

    sent_groups = bot.send_media_urls(
        source_code="bonus",
        source_name="Bonus",
        image_urls=image_urls,
        chunk_size=10,
        delay_seconds=settings.telegram_send_delay_seconds,
    )

    message = (
        "🔥 Promotii Bonus azi\n"
        f"📅 Valabil: {valid_from} - {valid_to}\n\n"
        "#bonus"
    )
    text_ok = bot.send_text(message, parse_mode="HTML", disable_web_page_preview=False)

    if sent_groups > 0:
        mark_posted("bonus", catalog_url)
    else:
        print("[WARN] Bonus pages were not sent; state not marked as posted.")

    print(
        "[INFO] Bonus catalog posted "
        f"catalog_url={catalog_url}, images={len(image_urls)}, groups={sent_groups}, message_sent={text_ok}, saved={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
