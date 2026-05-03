import sqlite3
from pathlib import Path
from typing import Dict, List

from core.normalizer import build_unique_key, clean_text, normalize_price


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_code TEXT NOT NULL,
            source_name TEXT,
            name TEXT NOT NULL,
            new_price TEXT NOT NULL,
            old_price TEXT,
            discount TEXT,
            category TEXT,
            image_url TEXT,
            product_url TEXT,
            valid_from TEXT,
            valid_to TEXT,
            unique_key TEXT NOT NULL UNIQUE,
            posted_to_telegram INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """

        with self._connect() as conn:
            conn.execute(query)
            conn.commit()

    def insert_new_products(self, products: List[Dict]) -> int:
        insert_query = """
        INSERT OR IGNORE INTO products (
            source_code,
            source_name,
            name,
            new_price,
            old_price,
            discount,
            category,
            image_url,
            product_url,
            valid_from,
            valid_to,
            unique_key,
            posted_to_telegram
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
        """

        inserted = 0
        with self._connect() as conn:
            cursor = conn.cursor()
            for product in products:
                source_code = clean_text(product.get("source_code"))
                source_name = clean_text(product.get("source_name"))
                name = clean_text(product.get("name"))
                new_price = normalize_price(product.get("new_price"))

                if not source_code or not name or not new_price:
                    print(
                        "[WARN] Skipping DB insert due to missing source_code/name/new_price: "
                        f"{product}"
                    )
                    continue

                unique_key = build_unique_key(source_code, name, new_price)

                params = (
                    source_code,
                    source_name,
                    name,
                    new_price,
                    normalize_price(product.get("old_price")),
                    clean_text(product.get("discount")),
                    clean_text(product.get("category")),
                    clean_text(product.get("image_url")),
                    clean_text(product.get("product_url")),
                    clean_text(product.get("valid_from")),
                    clean_text(product.get("valid_to")),
                    unique_key,
                )

                cursor.execute(insert_query, params)
                if cursor.rowcount == 1:
                    inserted += 1

            conn.commit()

        return inserted

    def get_unposted_products(self) -> List[Dict]:
        query = """
        SELECT *
        FROM products
        WHERE posted_to_telegram = 0
        ORDER BY id ASC;
        """

        with self._connect() as conn:
            rows = conn.execute(query).fetchall()

        return [dict(row) for row in rows]

    def mark_products_as_posted(self, product_ids: List[int]) -> None:
        if not product_ids:
            return

        placeholders = ",".join("?" for _ in product_ids)
        query = f"UPDATE products SET posted_to_telegram = 1 WHERE id IN ({placeholders});"

        with self._connect() as conn:
            conn.execute(query, product_ids)
            conn.commit()
