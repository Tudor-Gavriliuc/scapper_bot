from typing import Dict, List
import ast
import json
import mimetypes
import os
import time

import requests

from core.normalizer import get_product_discount_percentage


class TelegramBot:
    def __init__(self, token: str, channel_id: str) -> None:
        self.token = token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def _format_message(self, product: Dict) -> str:
        name = product.get("name", "")
        source_name = product.get("source_name", "")
        new_price = product.get("new_price", "")
        old_price = product.get("old_price", "")
        discount = product.get("discount", "")
        product_url = product.get("product_url", "")
        valid_from = product.get("valid_from", "")
        valid_to = product.get("valid_to", "")

        lines = [
            f"🏪 Magazin: {source_name}",
            f"🛒 Produs: {name}",
            f"💰 Pret nou: {new_price}",
            f"🏷️ Pret vechi: {old_price or '-'}",
        ]

        if discount:
            lines.append(f"📉 Reducere: {discount}")
        if valid_from or valid_to:
            lines.append(f"📅 Perioada: {valid_from} - {valid_to}")
        if product_url:
            lines.append(f"🔗 Link: {product_url}")

        return "\n".join(lines)

    def _post_with_retry(self, endpoint: str, payload: Dict) -> bool:
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(endpoint, json=payload, timeout=20)

                if response.status_code == 429:
                    retry_after = 2
                    try:
                        data = response.json()
                        retry_after = int(
                            data.get("parameters", {}).get("retry_after", retry_after)
                        )
                    except Exception:
                        pass

                    print(
                        "[WARN] Telegram rate limit hit. "
                        f"Retrying in {retry_after}s (attempt {attempt}/{max_attempts})."
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    print(f"[ERROR] Telegram API returned error: {data}")
                    return False

                return True
            except requests.RequestException as exc:
                if attempt == max_attempts:
                    print(f"[ERROR] Telegram request failed: {exc}")
                    return False
                time.sleep(2)

        return False

    def send_product_promotion(self, product: Dict) -> bool:
        if not product.get("name") or not product.get("new_price"):
            print(
                "[WARN] Telegram skip, product has missing name/new_price: "
                f"id={product.get('id')}"
            )
            return False

        message = self._format_message(product)
        image_url = self._extract_image_url(product.get("image_url", ""))

        if image_url:
            photo_endpoint = f"{self.base_url}/sendPhoto"
            photo_payload = {
                "chat_id": self.channel_id,
                "photo": image_url,
                "caption": message[:1024],
            }
            if self._post_with_retry(photo_endpoint, photo_payload):
                print(f"[INFO] Telegram posted product id={product.get('id')} with image")
                return True

            print(
                "[WARN] sendPhoto failed, falling back to sendMessage for "
                f"id={product.get('id')}"
            )

        message_endpoint = f"{self.base_url}/sendMessage"
        message_payload = {
            "chat_id": self.channel_id,
            "text": message,
            "disable_web_page_preview": False,
        }
        if self._post_with_retry(message_endpoint, message_payload):
            print(f"[INFO] Telegram posted product id={product.get('id')}")
            return True

        return False

    def _format_batch_message(
        self,
        source_code: str,
        source_name: str,
        products: List[Dict],
    ) -> str:
        if (source_code or "").strip().lower() in {"local", "magazine"}:
            valid_from = ""
            valid_to = ""
            for p in products:
                valid_from = valid_from or (p.get("valid_from") or "").strip()
                valid_to = valid_to or (p.get("valid_to") or "").strip()

            lines = [f"🔥 Promotii {source_name} azi", ""]
            if valid_from or valid_to:
                lines.append(f"📅 Valabil: {valid_from} - {valid_to}")
            lines.extend(["", "#local"])
            return "\n".join(lines)

        lines = [f"🔥 Promotii {source_name} azi", ""]

        for product in products:
            name = (product.get("name") or "").strip()
            new_price = (product.get("new_price") or "").strip()
            old_price = (product.get("old_price") or "").strip()
            pct = get_product_discount_percentage(product)
            discount_tag = f" 🔻{int(pct)}%" if pct else ""

            if old_price:
                line = f"🛍️ {name} - <b>{new_price}</b> (vechi: {old_price}){discount_tag}"
            else:
                line = f"🛍️ {name} - <b>{new_price}</b>{discount_tag}"
            lines.append(line)

        # Add validity period if any product in the batch has it (all share the same dates).
        valid_from = ""
        valid_to = ""
        for p in products:
            valid_from = valid_from or (p.get("valid_from") or "").strip()
            valid_to = valid_to or (p.get("valid_to") or "").strip()
        if valid_from or valid_to:
            lines.append(f"\n📅 Valabil: {valid_from} - {valid_to}")

        lines.extend(["", f"#{(source_code or '').lower()}"])
        return "\n".join(lines)

    def send_batch_promotions(
        self,
        source_code: str,
        source_name: str,
        products: List[Dict],
    ) -> bool:
        if not products:
            return False

        message = self._format_batch_message(source_code, source_name, products)
        media_sent = self._send_batch_media_group(source_code, source_name, products)

        # Always send a separate description text for the batch.
        text_sent = self._send_text_batch(message)
        return media_sent or text_sent

    def _send_text_batch(self, message: str) -> bool:
        return self.send_text(message, parse_mode="HTML", disable_web_page_preview=True)

    def send_text(
        self,
        message: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> bool:
        endpoint = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        return self._post_with_retry(endpoint, payload)

    def send_media_urls(
        self,
        source_code: str,
        source_name: str,
        image_urls: List[str],
        chunk_size: int = 10,
        delay_seconds: float = 1.1,
    ) -> int:
        clean_urls = [u.strip() for u in image_urls if (u or "").strip()]
        if not clean_urls:
            return 0

        endpoint = f"{self.base_url}/sendMediaGroup"
        chunk_size = max(1, min(chunk_size, 10))
        sent_groups = 0

        for i in range(0, len(clean_urls), chunk_size):
            chunk = clean_urls[i : i + chunk_size]
            media_items = [{"type": "photo", "media": url} for url in chunk]
            payload = {
                "chat_id": self.channel_id,
                "media": media_items,
            }
            ok = self._post_with_retry(endpoint, payload)
            if ok:
                sent_groups += 1
                print(
                    "[INFO] Telegram posted media group "
                    f"source={source_code}, source_name={source_name}, images={len(chunk)}"
                )
            else:
                print(
                    "[WARN] Telegram media group failed "
                    f"source={source_code}, source_name={source_name}, images={len(chunk)}"
                )

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        return sent_groups

    def _send_batch_media_group(
        self,
        source_code: str,
        source_name: str,
        products: List[Dict],
    ) -> bool:
        # Only include products with a valid image
        products_with_images = [p for p in products if self._extract_image_url(p.get("image_url"))]
        if not products_with_images:
            print("[WARN] No products with images to post in media group.")
            return False

        # Telegram accepts up to 10 media items per group.
        products_with_images = products_with_images[:10]

        media_items = []
        for product in products_with_images:
            image_url = self._extract_image_url(product.get("image_url"))
            media_items.append({
                "type": "photo",
                "media": image_url,
            })

        endpoint = f"{self.base_url}/sendMediaGroup"

        # Local file paths cannot be fetched by Telegram via URL, upload directly.
        has_local_files = any(not str(item.get("media") or "").startswith("http") for item in media_items)
        if has_local_files:
            uploaded_ok = self._send_media_group_as_uploaded_files(endpoint, media_items)
            if uploaded_ok:
                print(
                    "[INFO] Telegram posted uploaded media batch "
                    f"source={source_code}, source_name={source_name}, images={len(media_items)}"
                )
                return True

        payload = {
            "chat_id": self.channel_id,
            "media": media_items,
        }
        ok = self._post_with_retry(endpoint, payload)
        if ok:
            print(
                "[INFO] Telegram posted media batch "
                f"source={source_code}, source_name={source_name}, images={len(media_items)}"
            )
            return True

        # Fallback 1: upload media as files (attach://) when Telegram cannot fetch URLs.
        uploaded_ok = self._send_media_group_as_uploaded_files(endpoint, media_items)
        if uploaded_ok:
            print(
                "[WARN] Telegram media URL batch failed; uploaded files succeeded "
                f"source={source_code}, source_name={source_name}, images={len(media_items)}"
            )
            return True

        # Fallback 2: try sending images one by one so one bad URL does not fail all.
        sent_count = 0
        photo_endpoint = f"{self.base_url}/sendPhoto"
        for media in media_items:
            photo_payload = {
                "chat_id": self.channel_id,
                "photo": media["media"],
            }
            if self._post_with_retry(photo_endpoint, photo_payload):
                sent_count += 1

        if sent_count:
            print(
                "[WARN] Telegram media batch failed; fallback sendPhoto succeeded "
                f"source={source_code}, sent_images={sent_count}/{len(media_items)}"
            )
            return True

        print(f"[WARN] Telegram media batch failed source={source_code}")
        return False

    def _send_media_group_as_uploaded_files(
        self,
        endpoint: str,
        media_items: List[Dict],
    ) -> bool:
        upload_entries = []
        for idx, media in enumerate(media_items):
            image_url = str(media.get("media") or "").strip()
            if not image_url:
                continue

            downloaded = self._download_image_bytes(image_url)
            if not downloaded:
                continue

            content, content_type = downloaded
            upload_entries.append((idx, content, content_type))

        if not upload_entries:
            return False

        files = {}
        uploaded_media = []
        for idx, content, content_type in upload_entries:
            attach_name = f"file{idx}"
            ext = ".jpg"
            if content_type == "image/png":
                ext = ".png"
            elif content_type == "image/webp":
                ext = ".webp"

            filename = f"image_{idx}{ext}"
            files[attach_name] = (filename, content, content_type)
            uploaded_media.append(
                {
                    "type": "photo",
                    "media": f"attach://{attach_name}",
                }
            )

        if not uploaded_media:
            return False

        form_data = {
            "chat_id": self.channel_id,
            "media": json.dumps(uploaded_media),
        }

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(endpoint, data=form_data, files=files, timeout=35)
                if response.status_code == 429:
                    retry_after = 2
                    try:
                        retry_after = int(
                            response.json().get("parameters", {}).get("retry_after", retry_after)
                        )
                    except Exception:
                        pass
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    return True

                print(f"[WARN] Telegram uploaded media group API error: {data}")
                return False
            except requests.RequestException as exc:
                if attempt == max_attempts:
                    print(f"[WARN] Telegram uploaded media group failed: {exc}")
                    return False
                time.sleep(2)

        return False

    def _download_image_bytes(self, image_url: str) -> tuple[bytes, str] | None:
        local_path = str(image_url or "").strip()
        if local_path and os.path.isfile(local_path):
            try:
                with open(local_path, "rb") as f:
                    content = f.read()
            except OSError as exc:
                print(f"[WARN] Local image read failed for Telegram upload: path={local_path}, err={exc}")
                return None

            if not content:
                return None

            guessed = mimetypes.guess_type(local_path)[0] or "image/jpeg"
            if not guessed.startswith("image/"):
                guessed = "image/jpeg"
            return content, guessed

        try:
            response = requests.get(image_url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WARN] Image download failed for Telegram upload: url={image_url}, err={exc}")
            return None

        content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith("image/"):
            print(
                "[WARN] Image download returned non-image content-type "
                f"url={image_url}, content_type={content_type}"
            )
            return None

        content = response.content or b""
        if not content:
            return None

        if not content_type:
            content_type = "image/jpeg"

        return content, content_type

    def _extract_image_url(self, raw_value) -> str:
        if isinstance(raw_value, str):
            text = raw_value.strip()
            if text.startswith("http"):
                return text

            # Local file path support for OCR-cropped images.
            if text:
                normalized = os.path.abspath(text)
                if os.path.isfile(normalized):
                    return normalized

            # Some rows may contain a serialized dict from older runs.
            if text.startswith("{") and text.endswith("}"):
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, dict):
                        return self._extract_image_url(parsed)
                except Exception:
                    return ""
            return ""

        if isinstance(raw_value, dict):
            preferred_keys = ("s350x350", "s200x200", "s150x150", "s1350x1350")
            for key in preferred_keys:
                candidate = str(raw_value.get(key) or "").strip()
                if candidate.startswith("http"):
                    return candidate

            for value in raw_value.values():
                candidate = str(value or "").strip()
                if candidate.startswith("http"):
                    return candidate

        return ""
