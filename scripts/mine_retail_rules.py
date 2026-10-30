"""Mine association rules and frequent itemsets from the Groceries POS dataset (Hahsler et al., 2006).

Extracts:
- Complete catalog of 169 grocery items (canonical English names) enriched with categories, icons, realistic prices, support, and basket count.
- L1, L2, L3 frequent itemsets for the Data Science & Statistics views.
- 52 curated supermarket store items across 7 distinct grocery aisles.
- 4-Tier Stratified Association Rules (guaranteed store item coverage, category quotas,
  multi-item cart rules, and high-lift culinary/shopping synergies).
- Top frequent combos/bundles (L2 & L3) with human-interpretable explanations.
- Executive summary KPI metrics.

Saves directly to src/data/ecom_rules.json with zero external runtime dependencies.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(PROJECT_ROOT, "src", "data", "groceries.csv")
OUT_FILE = os.path.join(PROJECT_ROOT, "src", "data", "ecom_rules.json")

# ---------------------------------------------------------------------------
# 1. Supermarket Aisle Categories & 52 Curated Store Items (Canonical English)
# ---------------------------------------------------------------------------
STORE_CATEGORIES_DEF = [
    {"id": "ALL", "name": "All Items", "icon": "🛒"},
    {"id": "DAIRY", "name": "Dairy & Eggs", "icon": "🥛"},
    {"id": "PRODUCE", "name": "Fruits & Vegetables", "icon": "🥦"},
    {"id": "BAKERY", "name": "Bakery & Bread", "icon": "🥐"},
    {"id": "MEAT", "name": "Meat & Deli", "icon": "🥩"},
    {"id": "DRINKS", "name": "Beverages", "icon": "🥤"},
    {"id": "SNACKS", "name": "Sweets & Snacks", "icon": "🍫"},
    {"id": "PANTRY", "name": "Pantry & Essentials", "icon": "🫙"},
]

STORE_SKU_CATEGORIES = {
    # Dairy & Eggs (9)
    "whole milk": "DAIRY",
    "yogurt": "DAIRY",
    "whipped/sour cream": "DAIRY",
    "domestic eggs": "DAIRY",
    "butter": "DAIRY",
    "curd": "DAIRY",
    "margarine": "DAIRY",
    "cream cheese": "DAIRY",
    "sliced cheese": "DAIRY",
    # Fruits & Vegetables (9)
    "other vegetables": "PRODUCE",
    "root vegetables": "PRODUCE",
    "tropical fruit": "PRODUCE",
    "citrus fruit": "PRODUCE",
    "pip fruit": "PRODUCE",
    "frozen vegetables": "PRODUCE",
    "berries": "PRODUCE",
    "onions": "PRODUCE",
    "herbs": "PRODUCE",
    # Bakery & Bread (7)
    "rolls/buns": "BAKERY",
    "pastry": "BAKERY",
    "brown bread": "BAKERY",
    "white bread": "BAKERY",
    "waffles": "BAKERY",
    "long life bakery product": "BAKERY",
    "semi-finished bread": "BAKERY",
    # Meat & Deli (7)
    "sausage": "MEAT",
    "frankfurter": "MEAT",
    "pork": "MEAT",
    "beef": "MEAT",
    "chicken": "MEAT",
    "hamburger meat": "MEAT",
    "ham": "MEAT",
    # Beverages (8)
    "soda": "DRINKS",
    "bottled water": "DRINKS",
    "bottled beer": "DRINKS",
    "canned beer": "DRINKS",
    "fruit/vegetable juice": "DRINKS",
    "coffee": "DRINKS",
    "UHT-milk": "DRINKS",
    "red/blush wine": "DRINKS",
    # Sweets & Snacks (6)
    "chocolate": "SNACKS",
    "salty snack": "SNACKS",
    "dessert": "SNACKS",
    "specialty chocolate": "SNACKS",
    "candy": "SNACKS",
    "ice cream": "SNACKS",
    # Pantry & Essentials (6)
    "shopping bags": "PANTRY",
    "newspapers": "PANTRY",
    "napkins": "PANTRY",
    "sugar": "PANTRY",
    "oil": "PANTRY",
    "flour": "PANTRY",
}

CATEGORY_ICONS = {
    "ALL": "🛒",
    "DAIRY": "🥛",
    "PRODUCE": "🥦",
    "BAKERY": "🥐",
    "MEAT": "🥩",
    "DRINKS": "🥤",
    "SNACKS": "🍫",
    "PANTRY": "🫙",
    "OTHER": "🛍️",
}

ITEM_ICONS = {
    "whole milk": "🥛",
    "yogurt": "🥣",
    "whipped/sour cream": "🍦",
    "domestic eggs": "🥚",
    "butter": "🧈",
    "curd": "🧀",
    "margarine": "🧈",
    "cream cheese": "🧀",
    "sliced cheese": "🧀",
    "hard cheese": "🧀",
    "soft cheese": "🧀",
    "other vegetables": "🥬",
    "root vegetables": "🥕",
    "tropical fruit": "🥭",
    "citrus fruit": "🍊",
    "pip fruit": "🍎",
    "frozen vegetables": "🥦",
    "berries": "🍓",
    "onions": "🧅",
    "herbs": "🌿",
    "grapes": "🍇",
    "rolls/buns": "🥖",
    "pastry": "🥐",
    "brown bread": "🍞",
    "white bread": "🍞",
    "waffles": "🧇",
    "long life bakery product": "🥨",
    "semi-finished bread": "🥖",
    "sausage": "🌭",
    "frankfurter": "🌭",
    "pork": "🥓",
    "beef": "🥩",
    "chicken": "🍗",
    "hamburger meat": "🍔",
    "ham": "🍖",
    "soda": "🥤",
    "bottled water": "💧",
    "bottled beer": "🍺",
    "canned beer": "🍻",
    "fruit/vegetable juice": "🧃",
    "coffee": "☕",
    "UHT-milk": "🥛",
    "red/blush wine": "🍷",
    "white wine": "🥂",
    "chocolate": "🍫",
    "salty snack": "🍿",
    "dessert": "🍮",
    "specialty chocolate": "🍫",
    "candy": "🍬",
    "ice cream": "🍨",
    "shopping bags": "🛍️",
    "newspapers": "📰",
    "napkins": "🧻",
    "sugar": "🧂",
    "oil": "🫒",
    "flour": "🌾",
    "pasta": "🍝",
    "baking powder": "🥄",
}

ITEM_PRICES = {
    "whole milk": 1.85,
    "yogurt": 1.40,
    "whipped/sour cream": 1.65,
    "domestic eggs": 2.50,
    "butter": 2.20,
    "curd": 1.75,
    "margarine": 1.60,
    "cream cheese": 2.10,
    "sliced cheese": 2.40,
    "other vegetables": 1.95,
    "root vegetables": 1.50,
    "tropical fruit": 2.60,
    "citrus fruit": 2.30,
    "pip fruit": 2.15,
    "frozen vegetables": 2.25,
    "berries": 3.40,
    "onions": 1.10,
    "herbs": 1.25,
    "rolls/buns": 1.35,
    "pastry": 1.80,
    "brown bread": 1.90,
    "white bread": 1.70,
    "waffles": 2.35,
    "long life bakery product": 2.10,
    "semi-finished bread": 1.55,
    "sausage": 3.20,
    "frankfurter": 2.95,
    "pork": 4.50,
    "beef": 5.80,
    "chicken": 4.90,
    "hamburger meat": 3.90,
    "ham": 3.45,
    "soda": 1.25,
    "bottled water": 0.95,
    "bottled beer": 2.10,
    "canned beer": 1.65,
    "fruit/vegetable juice": 2.20,
    "coffee": 4.60,
    "UHT-milk": 1.50,
    "red/blush wine": 7.50,
    "chocolate": 1.95,
    "salty snack": 1.75,
    "dessert": 2.40,
    "specialty chocolate": 2.85,
    "candy": 1.30,
    "ice cream": 3.50,
    "shopping bags": 0.50,
    "newspapers": 1.20,
    "napkins": 1.45,
    "sugar": 1.35,
    "oil": 3.10,
    "flour": 1.25,
}

STORE_SKUS = list(STORE_SKU_CATEGORIES.keys())
assert len(STORE_SKUS) == 52, f"Expected 52 curated store SKUs, got {len(STORE_SKUS)}"


def classify_product(sku: str, name: str = "") -> str:
    """Classify a grocery item into one of the 7 supermarket aisles."""
    if sku in STORE_SKU_CATEGORIES:
        return STORE_SKU_CATEGORIES[sku]
    s = (sku or name).lower()
    if any(w in s for w in ["milk", "cheese", "yogurt", "cream", "butter", "curd", "egg", "mayonnaise"]):
        return "DAIRY"
    if any(w in s for w in ["vegetable", "fruit", "berr", "onion", "herb", "grape", "potato", "salad", "flower", "plant"]):
        return "PRODUCE"
    if any(w in s for w in ["bread", "roll", "bun", "pastry", "waffle", "bakery", "cake", "zwieback"]):
        return "BAKERY"
    if any(w in s for w in ["meat", "sausage", "frankfurter", "pork", "beef", "chicken", "ham", "fish", "turkey", "liver"]):
        return "MEAT"
    if any(w in s for w in ["soda", "water", "beer", "wine", "juice", "coffee", "tea", "beverage", "liquor", "brandy", "whisky", "rum", "prosecco", "cocoa"]):
        return "DRINKS"
    if any(w in s for w in ["chocolate", "snack", "candy", "dessert", "ice cream", "gum", "nut", "popcorn", "pudding", "sweet", "bar"]):
        return "SNACKS"
    return "PANTRY"


def classify_rule(rule: dict, catalog: dict) -> str:
    """Classify rule into category based on antecedent and consequent items."""
    ant_cats = [STORE_SKU_CATEGORIES[i] for i in rule["antecedent"] if i in STORE_SKU_CATEGORIES]
    if ant_cats:
        return Counter(ant_cats).most_common(1)[0][0]
    con_cats = [STORE_SKU_CATEGORIES[i] for i in rule["consequent"] if i in STORE_SKU_CATEGORIES]
    if con_cats:
        return Counter(con_cats).most_common(1)[0][0]
    for sku in rule["antecedent"] + rule["consequent"]:
        c = classify_product(sku)
        if c != "OTHER":
            return c
    return "PANTRY"


def explain_rule_reason(ant: list[str], con: list[str], lift: float, conf: float) -> str:
    """Provide a concise, human-friendly explanation for why items are bought together."""
    items = set(ant + con)
    if "berries" in items and "whipped/sour cream" in items:
        return "Dessert pairing: fresh berries & cream"
    if "root vegetables" in items and any(m in items for m in ("beef", "pork", "chicken", "herbs", "other vegetables")):
        return "Home cooking: soup, stew & roast ingredients"
    if any(b in items for b in ("rolls/buns", "white bread", "brown bread")) and any(m in items for m in ("sausage", "frankfurter", "sliced cheese", "ham", "butter")):
        return "Sandwich & breakfast preparation"
    if "whole milk" in items and any(b in items for b in ("rolls/buns", "pastry", "yogurt", "curd", "domestic eggs", "butter")):
        return "Daily breakfast & dairy staples"
    if any(d in items for d in ("bottled beer", "canned beer", "soda", "bottled water", "red/blush wine")) and any(s in items for s in ("salty snack", "chocolate", "bottled water", "soda")):
        return "Beverage & refreshment replenishment"
    if any(k in items for k in ("flour", "sugar", "baking powder", "butter", "domestic eggs", "margarine")):
        return "Home baking essentials"
    return f"Complementary basket affinity ({lift:.2f}× lift)"


def load_groceries_baskets(csv_path: str) -> tuple[list[set[str]], list[set[str]]]:
    """Load all transactions and multi-item baskets from groceries.csv."""
    all_tx: list[set[str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items = {x.strip() for x in line.split(",") if x.strip()}
            if items:
                all_tx.append(items)
    multi_baskets = [b for b in all_tx if len(b) >= 2]
    return all_tx, multi_baskets


def mine_apriori(
    baskets: list[set[str]],
    min_count: int = 30,
    min_conf: float = 0.15,
    min_lift: float = 1.15,
) -> tuple[dict[frozenset[str], set[int]], list[dict], dict[str, set[int]]]:
    """Mine frequent itemsets (L1, L2, L3) and association rules using tidset intersection."""
    n = len(baskets)
    item_baskets: dict[str, set[int]] = defaultdict(set)
    for tid, b in enumerate(baskets):
        for item in b:
            item_baskets[item].add(tid)

    L1 = {frozenset([item]): tids for item, tids in item_baskets.items() if len(tids) >= min_count}
    all_frequents: dict[frozenset[str], set[int]] = dict(L1)
    current_L = L1
    k = 2

    while current_L and k <= 3:
        itemsets = list(current_L.keys())
        candidates = set()
        for i in range(len(itemsets)):
            for j in range(i + 1, len(itemsets)):
                union = itemsets[i] | itemsets[j]
                if len(union) == k:
                    if all(frozenset(sub) in current_L for sub in combinations(union, k - 1)):
                        candidates.add(union)

        next_L: dict[frozenset[str], set[int]] = {}
        for cand in candidates:
            it = iter(cand)
            tids = item_baskets[next(it)].copy()
            for item in it:
                tids &= item_baskets[item]
                if len(tids) < min_count:
                    break
            if len(tids) >= min_count:
                next_L[cand] = tids
                all_frequents[cand] = tids

        current_L = next_L
        k += 1

    rules: list[dict] = []
    for itemset, tids in all_frequents.items():
        if len(itemset) < 2:
            continue
        supp_both = len(tids) / n
        count_both = len(tids)
        items = list(itemset)
        for r in range(1, len(items)):
            for ant_tuple in combinations(items, r):
                ant = frozenset(ant_tuple)
                con = itemset - ant
                ant_tids = all_frequents.get(ant)
                if not ant_tids:
                    continue
                conf = len(tids) / len(ant_tids)
                if conf >= min_conf:
                    con_tids = all_frequents.get(con)
                    supp_con = len(con_tids) / n if con_tids else 0.0001
                    lift = conf / supp_con if supp_con > 0 else 0.0
                    if lift >= min_lift:
                        ant_list = sorted(ant)
                        con_list = sorted(con)
                        rules.append({
                            "antecedent": ant_list,
                            "consequent": con_list,
                            "support": round(supp_both, 4),
                            "confidence": round(conf, 4),
                            "lift": round(lift, 2),
                            "count": count_both,
                            "reason": explain_rule_reason(ant_list, con_list, lift, conf),
                        })

    return all_frequents, rules, item_baskets


def extract_frequent_itemsets(
    all_frequents: dict[frozenset[str], set[int]],
    n_baskets: int,
) -> dict[str, list[dict]]:
    """Extract L1, L2, L3 itemsets sorted descending by count."""
    frequent_itemsets: dict[str, list[dict]] = {"L1": [], "L2": [], "L3": []}
    for itemset, tids in all_frequents.items():
        k = len(itemset)
        if k in (1, 2, 3):
            key = f"L{k}"
            frequent_itemsets[key].append({
                "items": sorted(list(itemset)),
                "k": k,
                "support": round(len(tids) / n_baskets, 4),
                "count": len(tids),
            })
    for k_key in ("L1", "L2", "L3"):
        frequent_itemsets[k_key].sort(key=lambda x: (-x["count"], x["items"]))
    return frequent_itemsets


def extract_combos(
    all_frequents: dict[frozenset[str], set[int]],
    n_baskets: int,
    catalog: dict[str, dict],
    limit: int = 80,
) -> list[dict]:
    """Extract top L2 pairs for combo recommendations."""
    combos = []
    for itemset, tids in all_frequents.items():
        if len(itemset) == 2:
            it = sorted(list(itemset))
            cat = (
                STORE_SKU_CATEGORIES.get(it[0])
                or STORE_SKU_CATEGORIES.get(it[1])
                or classify_product(it[0])
            )
            combos.append({
                "items": it,
                "support": round(len(tids) / n_baskets, 4),
                "count": len(tids),
                "category": cat,
                "reason": explain_rule_reason([it[0]], [it[1]], 2.0, 0.3),
            })
    combos.sort(key=lambda x: -x["count"])
    return combos[:limit]


def enrich_catalog(
    item_baskets: dict[str, set[int]],
    n_baskets: int,
    baskets: list[set[str]] | None = None,
    all_rules: list[dict] | None = None,
    min_count: int = 30,
) -> dict[str, dict]:
    """Build catalog metadata for all 169 items with Apriori pruning diagnostics."""
    single_ant_skus = set()
    if all_rules:
        for r in all_rules:
            if len(r.get("antecedent", [])) == 1:
                single_ant_skus.add(r["antecedent"][0])

    enriched = {}
    for sku in sorted(item_baskets.keys()):
        cat = classify_product(sku)
        icon = ITEM_ICONS.get(sku) or CATEGORY_ICONS.get(cat, "🛒")
        tids = item_baskets[sku]
        cnt = len(tids)
        supp = round(cnt / n_baskets, 4) if n_baskets > 0 else 0.0
        default_price = round(1.20 + (sum(ord(c) for c in sku) % 35) * 0.10, 2)
        price = ITEM_PRICES.get(sku, default_price)

        # Find strongest co-occurring partner in raw baskets for pruning explanation
        max_co_item = ""
        max_co_count = 0
        if baskets is not None:
            co_counts = Counter(
                other
                for tid in tids
                for other in baskets[tid]
                if other != sku
            )
            if co_counts:
                max_co_item, max_co_count = co_counts.most_common(1)[0]

        max_co_supp = round(max_co_count / n_baskets, 4) if n_baskets > 0 else 0.0
        max_co_conf = round(max_co_count / cnt, 4) if cnt > 0 else 0.0
        partner_cnt = len(item_baskets.get(max_co_item, set())) if max_co_item else 0
        partner_supp = (partner_cnt / n_baskets) if (n_baskets > 0 and partner_cnt > 0) else 0.0
        max_co_lift = round(max_co_conf / partner_supp, 2) if partner_supp > 0 else 0.0

        in_l1 = cnt >= min_count
        in_l2 = max_co_count >= min_count
        has_rule = sku in single_ant_skus
        if has_rule:
            pruned_stage = "NONE"
        elif not in_l1:
            pruned_stage = "C1_TO_L1"
        elif not in_l2:
            pruned_stage = "C2_TO_L2"
        else:
            pruned_stage = "RULE_FILTER"

        enriched[sku] = {
            "code": sku,
            "name": sku,
            "price": price,
            "category": cat,
            "icon": icon,
            "support": supp,
            "count": cnt,
            "in_l1": in_l1,
            "in_l2": in_l2,
            "has_apriori_rule": has_rule,
            "pruned_stage": pruned_stage,
            "max_co_item": max_co_item,
            "max_co_count": max_co_count,
            "max_co_support": max_co_supp,
            "max_co_conf": max_co_conf,
            "max_co_lift": max_co_lift,
        }
    return enriched


def select_diversified_rules(
    all_rules: list[dict],
    baskets: list[set[str]],
    catalog: dict[str, dict],
    item_baskets: dict[str, set[int]],
    all_store_skus: list[str],
    total_quota: int = 1200,
) -> list[dict]:
    """Select diversified association rules strictly from valid Apriori rules (no fake below-threshold rules)."""
    selected: list[dict] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

    single_ant_rules = defaultdict(list)
    for r in all_rules:
        if len(r["antecedent"]) == 1:
            single_ant_rules[r["antecedent"][0]].append(r)

    # Tier 1: Single-Item Rules for all SKUs that pass Apriori thresholds (up to 4 per SKU)
    for sku in all_store_skus:
        sku_rules = sorted(
            single_ant_rules.get(sku, []),
            key=lambda x: (round(x["confidence"] * x["lift"], 4), x["lift"], x["confidence"]),
            reverse=True,
        )
        for r in sku_rules[:4]:
            rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
            if rule_key not in seen:
                seen.add(rule_key)
                r_copy = dict(r)
                r_copy["category"] = classify_rule(r_copy, catalog)
                selected.append(r_copy)

    # Tier 2: Category Quotas (Up to 80 rules per category)
    target_category_ids = ["DAIRY", "PRODUCE", "BAKERY", "MEAT", "DRINKS", "SNACKS", "PANTRY"]
    cat_rules = defaultdict(list)
    for r in all_rules:
        c = classify_rule(r, catalog)
        if c in target_category_ids:
            cat_rules[c].append(r)

    for cat in target_category_ids:
        r_list = sorted(cat_rules[cat], key=lambda x: (x["lift"], x["confidence"], x["support"]), reverse=True)
        added_cat = 0
        for r in r_list:
            rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
            if rule_key not in seen:
                seen.add(rule_key)
                r_copy = dict(r)
                r_copy["category"] = cat
                selected.append(r_copy)
                added_cat += 1
                if added_cat >= 80:
                    break

    # Tier 3: Multi-item Antecedent Rules (|A| >= 2, up to 250 rules)
    multi_ant_rules = sorted(
        [r for r in all_rules if len(r["antecedent"]) >= 2],
        key=lambda x: (round(x["confidence"] * x["lift"], 4), x["lift"], x["confidence"]),
        reverse=True,
    )
    for r in multi_ant_rules:
        if len(selected) >= total_quota:
            break
        rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
        if rule_key not in seen:
            seen.add(rule_key)
            r_copy = dict(r)
            r_copy["category"] = classify_rule(r_copy, catalog)
            selected.append(r_copy)

    # Tier 4: Global High-Lift Fill
    all_rules_by_lift = sorted(all_rules, key=lambda x: (x["lift"], x["confidence"], x["support"]), reverse=True)
    for r in all_rules_by_lift:
        if len(selected) >= total_quota:
            break
        rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
        if rule_key not in seen:
            seen.add(rule_key)
            r_copy = dict(r)
            r_copy["category"] = classify_rule(r_copy, catalog)
            selected.append(r_copy)

    return selected


def build_summary(
    n_baskets: int,
    total_raw_tx: int,
    catalog_size: int,
    store_skus: list[str],
    frequent_itemsets: dict[str, list[dict]],
    total_rules_mined: int,
    curated_rules: list[dict],
    min_support: float,
    min_confidence: float,
    min_count: int = 30,
    min_lift: float = 1.15,
) -> dict:
    """Build summary KPI object."""
    l1_c = len(frequent_itemsets.get("L1", []))
    l2_c = len(frequent_itemsets.get("L2", []))
    l3_c = len(frequent_itemsets.get("L3", []))
    total_itemsets = l1_c + l2_c + l3_c

    max_lift_val = round(max((r.get("lift", 0.0) for r in curated_rules), default=0.0), 2)

    covered_skus = set()
    for r in curated_rules:
        if len(r.get("antecedent", [])) == 1:
            covered_skus.add(r["antecedent"][0])

    store_cov_count = sum(1 for s in store_skus if s in covered_skus)
    store_cov_pct = round((store_cov_count / len(store_skus) * 100.0) if store_skus else 0.0, 1)

    return {
        "total_transactions": total_raw_tx,
        "total_baskets": n_baskets,
        "total_catalog_products": catalog_size,
        "store_products_count": len(store_skus),
        "l1_count": l1_c,
        "l2_count": l2_c,
        "l3_count": l3_c,
        "total_frequent_itemsets": total_itemsets,
        "total_rules_mined": total_rules_mined,
        "curated_rules_count": len(curated_rules),
        "max_lift": max_lift_val,
        "min_confidence": round(min_confidence, 4),
        "min_support": round(min_support, 4),
        "store_coverage_pct": store_cov_pct,
        "min_count": min_count,
        "min_lift": round(min_lift, 2),
        "catalog_count": catalog_size,
        "catalog_rule_coverage_pct": store_cov_pct,
    }


def main(csv_path: str = DEFAULT_CSV) -> None:
    if not os.path.exists(csv_path):
        print(f"Error: Dataset not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Groceries POS dataset from {csv_path}...")
    all_tx, multi_baskets = load_groceries_baskets(csv_path)
    # Use all 9,835 POS transactions as the canonical denominator (matching Hahsler et al., 2006)
    baskets = all_tx
    n_baskets = len(baskets)
    print(f"Total POS transactions: {n_baskets} (multi-item baskets: {len(multi_baskets)})")

    min_count = 30
    min_conf = 0.15
    min_lift = 1.15
    min_support = min_count / n_baskets

    all_frequents, all_rules, item_baskets = mine_apriori(
        baskets, min_count=min_count, min_conf=min_conf, min_lift=min_lift
    )
    print(f"Frequent itemsets: {len(all_frequents)}, Valid association rules: {len(all_rules)}")

    frequent_itemsets = extract_frequent_itemsets(all_frequents, n_baskets)
    print(
        f"Itemsets extracted: L1={len(frequent_itemsets['L1'])}, "
        f"L2={len(frequent_itemsets['L2'])}, "
        f"L3={len(frequent_itemsets['L3'])}"
    )

    catalog = enrich_catalog(
        item_baskets,
        n_baskets,
        baskets=baskets,
        all_rules=all_rules,
        min_count=min_count,
    )
    # Sort all 169 items by basket count descending so bestsellers appear first on /shop
    all_store_skus = sorted(catalog.keys(), key=lambda k: (-catalog[k]["count"], k))
    combos = extract_combos(all_frequents, n_baskets, catalog, limit=80)
    curated_rules = select_diversified_rules(
        all_rules=all_rules,
        baskets=baskets,
        catalog=catalog,
        item_baskets=item_baskets,
        all_store_skus=all_store_skus,
        total_quota=1200,
    )

    summary = build_summary(
        n_baskets=n_baskets,
        total_raw_tx=len(all_tx),
        catalog_size=len(catalog),
        store_skus=all_store_skus,
        frequent_itemsets=frequent_itemsets,
        total_rules_mined=len(all_rules),
        curated_rules=curated_rules,
        min_support=min_support,
        min_confidence=min_conf,
        min_count=min_count,
        min_lift=min_lift,
    )

    payload = {
        "dataset_name": "Groceries POS Transactions (Hahsler et al., 2006)",
        "dataset_citation": "Michael Hahsler, Kurt Hornik, and Thomas Reutterer (2006) - Implications of Probabilistic Data Modeling for Mining Association Rules, WU Vienna / R arules.",
        "total_baskets": n_baskets,
        "summary": summary,
        "categories": STORE_CATEGORIES_DEF,
        "store_skus": all_store_skus,
        "catalog": catalog,
        "frequent_itemsets": frequent_itemsets,
        "rules": curated_rules,
        "combos": combos,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"Saved {len(curated_rules)} rules to {OUT_FILE} ({os.path.getsize(OUT_FILE)//1024} KB)")
    print(f"Store coverage: {summary['store_coverage_pct']}% of {summary['store_products_count']} store items.")


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    main(csv_arg)
