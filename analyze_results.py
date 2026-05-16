#!/usr/bin/env python
"""Analyze scraper results from database."""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/promotions.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("SCRAPER TEST RESULTS - DATABASE ANALYSIS")
print("=" * 80)
print()

# Check total products by source
print("[1] PRODUCTS BY SOURCE")
print("-" * 80)
cursor.execute("""
    SELECT source_code, source_name, COUNT(*) as count
    FROM products
    GROUP BY source_code
    ORDER BY count DESC
""")

for row in cursor.fetchall():
    print(f"  {row['source_name']:20s} ({row['source_code']:10s}): {row['count']:4d} products")

print()

# Check recently added products
print("[2] RECENTLY ADDED PRODUCTS (last 24 hours)")
print("-" * 80)

cursor.execute("""
    SELECT 
        source_name,
        name,
        new_price,
        old_price,
        discount,
        valid_to,
        posted_to_telegram,
        created_at
    FROM products
    WHERE date(created_at) = date('now')
    ORDER BY created_at DESC
    LIMIT 10
""")

results = cursor.fetchall()
if results:
    for i, row in enumerate(results, 1):
        posted = "✓" if row['posted_to_telegram'] else "✗"
        print(f"\n  {i}. [{posted}] {row['source_name']}")
        print(f"     Name: {row['name'][:60]}")
        print(f"     Price: {row['new_price']} MDL (was {row['old_price']}) - {row['discount']} off")
        print(f"     Valid until: {row['valid_to']}")
else:
    print("  No products added today")

print()

# Check posting status
print("[3] POSTING STATUS")
print("-" * 80)

cursor.execute("""
    SELECT 
        source_code,
        COUNT(*) as total,
        SUM(CASE WHEN posted_to_telegram = 1 THEN 1 ELSE 0 END) as posted,
        SUM(CASE WHEN posted_to_telegram = 0 THEN 1 ELSE 0 END) as unposted
    FROM products
    GROUP BY source_code
""")

for row in cursor.fetchall():
    pct = (row['posted'] / row['total'] * 100) if row['total'] > 0 else 0
    print(f"  {row['source_code']:10s}: {row['posted']:3d}/{row['total']:3d} posted ({pct:5.1f}%)")

print()

# Check products with discount > 30%
print("[4] PRODUCTS WITH DISCOUNT > 30%")
print("-" * 80)

cursor.execute("""
    SELECT 
        source_code,
        COUNT(*) as count
    FROM products
    WHERE CAST(REPLACE(discount, '%', '') AS FLOAT) > 30
    GROUP BY source_code
    ORDER BY count DESC
""")

for row in cursor.fetchall():
    print(f"  {row['source_code']:10s}: {row['count']} products")

# Total high discount
cursor.execute("""
    SELECT COUNT(*) as count
    FROM products
    WHERE CAST(REPLACE(discount, '%', '') AS FLOAT) > 30
""")
total = cursor.fetchone()['count']
print(f"  {'TOTAL':10s}: {total} products")

print()
print("[5] SAMPLE KAUFLAND PRODUCTS WITH HIGH DISCOUNTS (>30%)")
print("-" * 80)

cursor.execute("""
    SELECT 
        name,
        new_price,
        old_price,
        discount,
        posted_to_telegram,
        valid_to
    FROM products
    WHERE source_code = 'kaufland'
        AND CAST(REPLACE(discount, '%', '') AS FLOAT) > 30
    ORDER BY 
        CAST(REPLACE(discount, '%', '') AS FLOAT) DESC,
        created_at DESC
    LIMIT 5
""")

for i, row in enumerate(cursor.fetchall(), 1):
    posted_icon = "✓" if row['posted_to_telegram'] else "✗"
    print(f"\n  {i}. [{posted_icon}] {row['name'][:55]}")
    print(f"     {row['new_price']} MDL (was {row['old_price']}) - {row['discount']} off")
    print(f"     Valid until: {row['valid_to']}")

print()
print("[6] SCRAPER STATISTICS")
print("-" * 80)

cursor.execute("SELECT COUNT(*) as count FROM products")
total_products = cursor.fetchone()['count']
print(f"  Total products in database: {total_products}")

cursor.execute("SELECT COUNT(*) as count FROM products WHERE posted_to_telegram = 1")
posted = cursor.fetchone()['count']
print(f"  Products posted to Telegram: {posted}")

cursor.execute("SELECT COUNT(*) as count FROM products WHERE posted_to_telegram = 0")
unposted = cursor.fetchone()['count']
print(f"  Products waiting to post: {unposted}")

cursor.execute("""
    SELECT COUNT(*) as count FROM products 
    WHERE date(valid_to) < date('now')
""")
expired = cursor.fetchone()['count']
print(f"  Expired products: {expired}")

print()
print("=" * 80)

conn.close()
