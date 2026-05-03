from __future__ import annotations

import json
from pathlib import Path

from core.config import settings
from core.revista_state import mark_posted, was_posted
from core.telegram_bot import TelegramBot
from extract_nr1_booklet_images import OUTPUT_PATH, extract_today_booklet_images


def main() -> None:
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        print("[WARN] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID.")
        return

    payload = extract_today_booklet_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_channel_id)

    date_label = payload.get("booklet_date") or "-"
    booklet_url = payload.get("booklet_url") or ""

    if was_posted("nr1", booklet_url):
        print(f"[INFO] Nr1 already posted, skipping duplicate: {booklet_url}")
        return

    message = (
        "📰 Revista Nr1 de azi\n"
        f"📅 Data: {date_label}\n"
        f"🔗 Link: {booklet_url}"
    )
    bot.send_text(message, parse_mode="HTML", disable_web_page_preview=False)
    mark_posted("nr1", booklet_url)

    print(
        "[INFO] Nr1 booklet link sent "
        f"booklet_url={booklet_url}, saved={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
