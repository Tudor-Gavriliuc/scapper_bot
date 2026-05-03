from __future__ import annotations

import json

from core.config import settings
from core.revista_state import mark_posted, was_posted
from core.telegram_bot import TelegramBot
from extract_local_revista import OUTPUT_PATH, extract_local_revista_images


def main() -> None:
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        print("[WARN] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID.")
        return

    payload = extract_local_revista_images()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_channel_id)

    revista_url = payload.get("revista_url") or ""

    if was_posted("local", revista_url):
        print(f"[INFO] Local already posted, skipping duplicate: {revista_url}")
        return

    message = (
        "📰 Revista Local\n"
        f"🔗 Link: {revista_url}"
    )
    bot.send_text(message, parse_mode="HTML", disable_web_page_preview=False)
    mark_posted("local", revista_url)

    print(f"[INFO] Local revista link sent: {revista_url}")
    print(f"[INFO] Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
