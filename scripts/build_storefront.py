#!/usr/bin/env python3
"""Join the storefront catalog with the mined Apriori rules."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import unicodedata

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "src", "data")
RULES_FILE = os.path.join(DATA_DIR, "ecom_rules.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.csv")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.csv")
OUT_FILE = os.path.join(DATA_DIR, "store.json")

MIN_COMBO_COUNT = 40
MIN_COMBO_LIFT = 1.8
COMBO_LIMIT = 12
COMBO_DISCOUNT = 10
FREE_SHIPPING = 300000
NOT_SUGGESTED = {"shopping bags"}

MINED_FIELDS = (
    "support",
    "count",
    "in_l1",
    "in_l2",
    "has_apriori_rule",
    "pruned_stage",
    "max_co_item",
    "max_co_count",
    "max_co_support",
    "max_co_conf",
    "max_co_lift",
)


def slugify(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    with open(RULES_FILE, encoding="utf-8") as handle:
        rules = json.load(handle)

    categories = []
    category_ids = {}
    with open(CATEGORIES_FILE, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row["name"].strip()
            category_id = slugify(name)
            category_ids[name] = category_id
            categories.append(
                {
                    "id": category_id,
                    "name": name,
                    "icon": row["emoji"].strip(),
                    "color": row["color"].strip(),
                    "tagline": row["tagline"].strip(),
                }
            )

    mined_catalog = rules["catalog"]
    catalog = {}
    missing_items = []
    unknown_categories = set()
    with open(PRODUCTS_FILE, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            item = row["item"].strip()
            category_name = row["category"].strip()
            if item not in mined_catalog:
                missing_items.append(item)
                continue
            if category_name not in category_ids:
                unknown_categories.add(category_name)
                continue
            mined = mined_catalog[item]
            entry = {
                "display_name": row["name"].strip(),
                "unit": row["unit"].strip(),
                "price": int(row["price"]),
                "category": category_ids[category_name],
                "icon": row["emoji"].strip(),
            }
            for field in MINED_FIELDS:
                entry[field] = mined.get(field)
            catalog[item] = entry

    if missing_items:
        fail("Products absent from ecom_rules catalog: " + ", ".join(missing_items))
    if unknown_categories:
        fail("Products use unknown categories: " + ", ".join(sorted(unknown_categories)))

    counts = {}
    for level in ("L1", "L2", "L3"):
        for entry in rules["frequent_itemsets"][level]:
            counts[tuple(sorted(entry["items"]))] = entry["count"]

    total_baskets = rules["total_baskets"]
    item_count = {
        item: counts[(item,)]
        for item in catalog
        if (item,) in counts
    }

    candidates = []
    for size in (2, 3):
        for itemset, count in counts.items():
            if len(itemset) != size or count < MIN_COMBO_COUNT:
                continue
            lift = min(
                count * total_baskets / (counts[tuple(sorted(set(itemset) - {item}))] * item_count[item])
                for item in itemset
            )
            if lift < MIN_COMBO_LIFT:
                continue
            candidates.append((lift * math.log(count), lift, itemset, count))

    candidates.sort(key=lambda candidate: candidate[0], reverse=True)

    selected = []
    used_twice = set()
    for _, lift, itemset, count in candidates:
        if len(selected) >= COMBO_LIMIT:
            break
        items = set(itemset)
        if any(item in used_twice for item in items):
            continue
        if any(items <= set(combo["items"]) or set(combo["items"]) <= items for combo in selected):
            continue
        original_price = sum(catalog[item]["price"] for item in itemset)
        price = int(round(original_price * (100 - COMBO_DISCOUNT) / 100, -3))
        combo = {
            "id": "-".join(slugify(catalog[item]["display_name"]) for item in itemset),
            "items": list(itemset),
            "count": count,
            "support": round(count / total_baskets, 4),
            "lift": round(lift, 2),
            "discount": COMBO_DISCOUNT,
            "original_price": original_price,
            "price": price,
            "saving": original_price - price,
        }
        selected.append(combo)
        for item in itemset:
            used_twice.add(item)

    bestsellers = sorted(
        (item for item in catalog if item not in NOT_SUGGESTED),
        key=lambda item: catalog[item]["count"],
        reverse=True,
    )[:10]

    store = {
        "source": rules.get("dataset_name", "Groceries"),
        "currency": "VND",
        "categories": categories,
        "catalog": catalog,
        "bestsellers": bestsellers,
        "combos": selected,
        "discount": COMBO_DISCOUNT,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(store, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        f"{len(categories)} categories, {len(catalog)} catalog items, "
        f"{len(selected)} combos -> {os.path.relpath(OUT_FILE, PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
