#!/usr/bin/env python
"""Show actual product samples that were scraped and posted."""

import sqlite3

conn = sqlite3.connect('data/promotions.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("SAMPLE PRODUCTS SCRAPED AND POSTED TO TELEGRAM")
print("=" * 80)
print()

print("[KAUFLAND PRODUCTS - SAMPLES]")
print("-" * 80)

cursor.execute("""
    SELECT 
        name,
        new_price,
        old_price,
        discount,
        valid_from,
        valid_to,
        category
    FROM products
    WHERE source_code = 'kaufland'
    ORDER BY created_at DESC
    LIMIT 8
""")

for i, row in enumerate(cursor.fetchall(), 1):
    discount_val = row['discount'].replace('%', '')
    try:
        discount_pct = float(discount_val)
    except:
        discount_pct = 0
    
    indicator = "🔥" if discount_pct > 50 else "⭐" if discount_pct > 30 else "•"
    
    print(f"\n  {i}. {indicator} {row['name'][:60]}")
    print(f"     Category: {row['category']}")
    print(f"     Price: {row['new_price']} MDL (was {row['old_price']}) - {row['discount']} off")
    print(f"     Valid: {row['valid_from']} → {row['valid_to']}")

print()
print()
print("[LINELLA PRODUCTS - SAMPLES]")
print("-" * 80)

cursor.execute("""
    SELECT 
        name,
        new_price,
        old_price,
        discount,
        valid_from,
        valid_to,
        category
    FROM products
    WHERE source_code = 'linella'
    ORDER BY created_at DESC
    LIMIT 8
""")

for i, row in enumerate(cursor.fetchall(), 1):
    discount_val = row['discount'].replace('%', '')
    try:
        discount_pct = float(discount_val)
    except:
        discount_pct = 0
    
    indicator = "🔥" if discount_pct > 50 else "⭐" if discount_pct > 30 else "•"
    
    print(f"\n  {i}. {indicator} {row['name'][:60]}")
    print(f"     Category: {row['category']}")
    print(f"     Price: {row['new_price']} MDL (was {row['old_price']}) - {row['discount']} off")
    print(f"     Valid: {row['valid_from']} → {row['valid_to']}")

print()
print()
print("[DISTRIBUTION BY DISCOUNT LEVEL]")
print("-" * 80)

cursor.execute("""
    SELECT 
        source_code,
        CASE 
            WHEN CAST(REPLACE(discount, '%', '') AS FLOAT) < 10 THEN '0-10%'
            WHEN CAST(REPLACE(discount, '%', '') AS FLOAT) < 20 THEN '10-20%'
            WHEN CAST(REPLACE(discount, '%', '') AS FLOAT) < 30 THEN '20-30%'
            WHEN CAST(REPLACE(discount, '%', '') AS FLOAT) < 50 THEN '30-50%'
            ELSE '50%+'
        END as discount_range,
        COUNT(*) as count
    FROM products
    GROUP BY source_code, discount_range
    ORDER BY source_code, discount_range
""")

for row in cursor.fetchall():
    print(f"  {row['source_code']:10s} {row['discount_range']:10s}: {row['count']:2d} products")

print()
print("=" * 80)

conn.close()
