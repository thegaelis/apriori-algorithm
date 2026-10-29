"""Mine association rules and frequent itemsets from UCI Online Retail dataset.

Extracts:
- Complete catalog enriched with categories, icons, support, and basket count.
- L1, L2, L3 frequent itemsets for the Admin Data Science Portal.
- Curated store SKUs across 7 distinct retail merchandise categories.
- 4-Tier Stratified Association Rules (guaranteed store SKU coverage, category quotas,
  multi-item cart rules, and high-lift global outliers) eliminating the herb-marker choking defect.
- Top frequent combos/bundles for cross-sell merchandising.
- Executive summary KPI metrics with defensive backward-compatibility aliases.

Saves directly to src/data/ecom_rules.json with zero runtime dependencies.
"""
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from itertools import combinations
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "data", "ecom_rules.json")

NON_PRODUCT = {"POST", "D", "M", "C2", "DOT", "BANK CHARGES", "S", "AMAZONFEE", "B", "CRUK", "PADS", "m"}

# ---------------------------------------------------------------------------
# 1. Merchandise Category & Curated Store Inventory Definitions
# ---------------------------------------------------------------------------
STORE_CATEGORIES_DEF = [
    {"id": "ALL", "name": "Tất cả sản phẩm", "icon": "🛍️"},
    {"id": "BAG", "name": "Jumbo Bags", "icon": "👜"},
    {"id": "LUNCH", "name": "Lunch Bags", "icon": "🎒"},
    {"id": "HERB", "name": "Herb Markers", "icon": "🌿"},
    {"id": "BAKE", "name": "Tea & Baking", "icon": "🧁"},
    {"id": "HEART", "name": "Heart & Decor", "icon": "❤️"},
    {"id": "CLOCK", "name": "Vintage Clocks", "icon": "⏰"},
    {"id": "MUG", "name": "Mugs & Cups", "icon": "☕"},
]

STORE_SKU_CATEGORIES = {
    # Jumbo Bags (8)
    "85099B": "BAG", "23203": "BAG", "22386": "BAG", "23199": "BAG",
    "23201": "BAG", "23202": "BAG", "21929": "BAG", "20712": "BAG",
    # Lunch Bags (8)
    "20725": "LUNCH", "22383": "LUNCH", "20727": "LUNCH", "22382": "LUNCH",
    "20728": "LUNCH", "23209": "LUNCH", "22384": "LUNCH", "23206": "LUNCH",
    # Herb Markers (6)
    "22916": "HERB", "22917": "HERB", "22918": "HERB", "22919": "HERB",
    "22920": "HERB", "22921": "HERB",
    # Tea & Baking (8)
    "22423": "BAKE", "22720": "BAKE", "21212": "BAKE", "22699": "BAKE",
    "22697": "BAKE", "22139": "BAKE", "22138": "BAKE", "21977": "BAKE",
    # Heart & Decor (8)
    "85123A": "HEART", "22457": "HEART", "22469": "HEART", "22470": "HEART",
    "21733": "HEART", "84978": "HEART", "84378": "HEART", "23321": "HEART",
    # Vintage Clocks (8)
    "22727": "CLOCK", "22726": "CLOCK", "22728": "CLOCK", "22730": "CLOCK",
    "22193": "CLOCK", "22729": "CLOCK", "22725": "CLOCK", "22191": "CLOCK",
    # Mugs & Tableware (6)
    "22698": "MUG", "21086": "MUG", "21238": "MUG", "21084": "MUG",
    "21090": "MUG", "22059": "MUG",
}

CATEGORY_ICONS = {
    "ALL": "🛍️",
    "BAG": "👜",
    "LUNCH": "🎒",
    "HERB": "🌿",
    "BAKE": "🧁",
    "HEART": "❤️",
    "CLOCK": "⏰",
    "MUG": "☕",
    "OTHER": "🎁",
}

STORE_SKUS = list(STORE_SKU_CATEGORIES.keys())


# ---------------------------------------------------------------------------
# 2. Product and Rule Category Classifiers
# ---------------------------------------------------------------------------
def classify_product(sku: str, name: str) -> str:
    """Classify product into one of the 7 merchandise categories or OTHER."""
    if sku in STORE_SKU_CATEGORIES:
        return STORE_SKU_CATEGORIES[sku]
    n = (name or "").upper()
    if "LUNCH BAG" in n:
        return "LUNCH"
    if "JUMBO BAG" in n or "BAG" in n:
        return "BAG"
    if "HERB" in n or "MARKER" in n:
        return "HERB"
    if any(w in n for w in ["CAKE", "TEA", "BAK", "TIN"]):
        return "BAKE"
    if any(w in n for w in ["HEART", "HANGING", "WICKER"]):
        return "HEART"
    if "CLOCK" in n:
        return "CLOCK"
    if any(w in n for w in ["CUP", "MUG", "PLATE"]):
        return "MUG"
    return "OTHER"


def classify_rule(rule: dict, catalog: dict) -> str:
    """Classify rule into category, prioritizing curated items and antecedent."""
    # Check antecedent items first (shopper intent focus)
    ant_cats = [STORE_SKU_CATEGORIES[i] for i in rule["antecedent"] if i in STORE_SKU_CATEGORIES]
    if ant_cats:
        return Counter(ant_cats).most_common(1)[0][0]

    # Check consequent items
    con_cats = [STORE_SKU_CATEGORIES[i] for i in rule["consequent"] if i in STORE_SKU_CATEGORIES]
    if con_cats:
        return Counter(con_cats).most_common(1)[0][0]

    # Keyword fallback across all items in rule
    for sku in rule["antecedent"] + rule["consequent"]:
        name = catalog.get(sku, {}).get("name", "")
        c = classify_product(sku, name)
        if c != "OTHER":
            return c
    return "OTHER"


# ---------------------------------------------------------------------------
# 3. High-Performance Zero-Dependency OpenXML Parser
# ---------------------------------------------------------------------------
def load_shared(z: zipfile.ZipFile) -> list[str]:
    """Parse shared strings XML with streaming iterator."""
    out = []
    for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if el.tag == NS + "si":
            out.append("".join(t.text or "" for t in el.iter(NS + "t")))
            el.clear()
    return out


def iter_rows(path: str):
    """Stream tabular rows from sheet1.xml while clearing subtrees to keep RSS < 120MB."""
    with zipfile.ZipFile(path) as z:
        shared = load_shared(z)
        row: dict[str, object] = {}
        for _, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml"), events=("end",)):
            if el.tag == NS + "c":
                ref = el.get("r", "")
                m = re.match(r"[A-Z]+", ref)
                col = m.group(0) if m else ""
                t = el.get("t")
                v = el.find(NS + "v")
                val = None
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in el.iter(NS + "t"))
                elif v is not None and v.text is not None:
                    val = shared[int(v.text)] if t == "s" else v.text
                row[col] = val
                el.clear()
            elif el.tag == NS + "row":
                r = int(el.get("r"))
                if r > 1:
                    yield [row.get(c) for c in "ABCDEFGH"]
                row = {}
                el.clear()


# ---------------------------------------------------------------------------
# 4. Apriori Itemset & Association Rule Mining Engine
# ---------------------------------------------------------------------------
def mine_apriori(
    baskets: list[set[str]],
    min_count: int = 140,
    min_conf: float = 0.20,
    min_lift: float = 1.2,
) -> tuple[dict[frozenset[str], set[int]], list[dict], dict[str, set[int]]]:
    """Mine frequent itemsets and association rules using tidset intersection.

    Returns:
        all_frequents: Mapping of frozenset[str] -> set of transaction IDs.
        rules: All valid association rules satisfying min_conf and min_lift.
        item_baskets: Mapping of single SKU -> set of transaction IDs.
    """
    n = len(baskets)
    item_baskets: dict[str, set[int]] = defaultdict(set)
    for tid, b in enumerate(baskets):
        for item in b:
            item_baskets[item].add(tid)

    # 1-itemsets (L1)
    L1 = {frozenset([item]): tids for item, tids in item_baskets.items() if len(tids) >= min_count}
    all_frequents: dict[frozenset[str], set[int]] = dict(L1)
    current_L = L1
    k = 2

    # Candidate generation & pruning loop for k >= 2
    while current_L:
        itemsets = list(current_L.keys())
        candidates = set()
        for i in range(len(itemsets)):
            for j in range(i + 1, len(itemsets)):
                union = itemsets[i] | itemsets[j]
                if len(union) == k:
                    # Apriori prune: verify all (k-1) subsets are frequent
                    if all(frozenset(sub) in current_L for sub in combinations(union, k - 1)):
                        candidates.add(union)

        # Tid-set intersection & frequency filtering
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

    # Rule generation from all frequent itemsets with size >= 2
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
                        rules.append({
                            "antecedent": sorted(ant),
                            "consequent": sorted(con),
                            "support": round(supp_both, 4),
                            "confidence": round(conf, 4),
                            "lift": round(lift, 2),
                            "count": count_both,
                        })

    return all_frequents, rules, item_baskets


# ---------------------------------------------------------------------------
# 5. Frequent Itemsets ($L_1, L_2, L_3$) Extractor
# ---------------------------------------------------------------------------
def extract_frequent_itemsets(
    all_frequents: dict[frozenset[str], set[int]],
    n_baskets: int,
) -> dict[str, list[dict]]:
    """Extract L1, L2, L3 itemsets formatted with items, k, support, and count.

    Sorted descending by count, then ascending by items for determinism.
    """
    frequent_itemsets: dict[str, list[dict]] = {"L1": [], "L2": [], "L3": []}

    for itemset, tids in all_frequents.items():
        k = len(itemset)
        if k in (1, 2, 3):
            key = f"L{k}"
            supp = round(len(tids) / n_baskets, 4)
            count = len(tids)
            frequent_itemsets[key].append({
                "items": sorted(list(itemset)),
                "k": k,
                "support": supp,
                "count": count,
            })

    for k_key in ("L1", "L2", "L3"):
        frequent_itemsets[k_key].sort(key=lambda x: (-x["count"], x["items"]))

    return frequent_itemsets


# ---------------------------------------------------------------------------
# 6. Combos / Bundles Extractor
# ---------------------------------------------------------------------------
def extract_combos(
    all_frequents: dict[frozenset[str], set[int]],
    n_baskets: int,
    catalog: dict[str, dict],
    limit: int = 80,
) -> list[dict]:
    """Extract top L2 pairs for combo bundle recommendations."""
    combos = []
    for itemset, tids in all_frequents.items():
        if len(itemset) == 2:
            it = sorted(list(itemset))
            cat = (
                STORE_SKU_CATEGORIES.get(it[0])
                or STORE_SKU_CATEGORIES.get(it[1])
                or classify_product(it[0], catalog.get(it[0], {}).get("name", ""))
            )
            combos.append({
                "items": it,
                "support": round(len(tids) / n_baskets, 4),
                "count": len(tids),
                "category": cat,
            })
    combos.sort(key=lambda x: -x["count"])
    return combos[:limit]


# ---------------------------------------------------------------------------
# 7. Catalog Enrichment
# ---------------------------------------------------------------------------
def enrich_catalog(
    raw_catalog: dict[str, dict],
    item_baskets: dict[str, set[int]],
    n_baskets: int,
) -> dict[str, dict]:
    """Enrich all catalog products with category, icon, support, and basket count."""
    enriched = {}
    for sku, p in raw_catalog.items():
        cat = classify_product(sku, p.get("name", ""))
        icon = CATEGORY_ICONS.get(cat, "🎁")
        cnt = len(item_baskets.get(sku, set()))
        supp = round(cnt / n_baskets, 4) if n_baskets > 0 else 0.0
        enriched[sku] = {
            "code": sku,
            "name": p.get("name", ""),
            "price": round(float(p.get("price", 2.50)), 2),
            "category": cat,
            "icon": icon,
            "support": supp,
            "count": cnt,
        }
    return enriched


# ---------------------------------------------------------------------------
# 8. 4-Tier Stratified Rule Selection Engine
# ---------------------------------------------------------------------------
def select_diversified_rules(
    all_rules: list[dict],
    baskets: list[set[str]],
    catalog: dict[str, dict],
    item_baskets: dict[str, set[int]],
    total_quota: int = 1000,
) -> list[dict]:
    """Select diversified association rules through 4-tier stratified allocation.

    Tier 1: Guaranteed Store Catalog Coverage (up to 5 per SKU, ranked by conf * lift).
    Tier 2: Category Quotas (up to 80 per category, ranked by lift).
    Tier 3: Multi-item Antecedent Rules (|A| >= 2, up to 200, cap 30/category).
    Tier 4: Global High-Lift Fill (up to total_quota).
    """
    n_baskets = len(baskets)
    selected: list[dict] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

    # Pre-index single-item antecedent rules
    single_ant_rules = defaultdict(list)
    for r in all_rules:
        if len(r["antecedent"]) == 1:
            single_ant_rules[r["antecedent"][0]].append(r)

    # -----------------------------------------------------------------------
    # TIER 1: Per-SKU Guaranteed Single-Item Rules (up to 5 per SKU)
    # -----------------------------------------------------------------------
    for sku in STORE_SKUS:
        # Rank by Confidence * Lift to ensure conversion and strong association
        sku_rules = sorted(
            single_ant_rules.get(sku, []),
            key=lambda x: (round(x["confidence"] * x["lift"], 4), x["lift"], x["confidence"]),
            reverse=True,
        )
        added_sku = 0
        for r in sku_rules[:5]:
            rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
            if rule_key not in seen:
                seen.add(rule_key)
                r_copy = dict(r)
                r_copy["category"] = classify_rule(r_copy, catalog)
                selected.append(r_copy)
                added_sku += 1

        # Fallback for store SKUs with counts below global mining threshold (e.g. 22059)
        if added_sku == 0:
            sku_baskets = [b for b in baskets if sku in b]
            if sku_baskets:
                co_counts = Counter(i for b in sku_baskets for i in b if i != sku)
                for cand_item, cnt in co_counts.most_common(10):
                    conf = cnt / len(sku_baskets)
                    cand_basket_count = len(item_baskets.get(cand_item, set()))
                    supp_cand = cand_basket_count / n_baskets if n_baskets > 0 else 0.0
                    lift = conf / supp_cand if supp_cand > 0 else 1.0
                    if cnt >= 40 and conf >= 0.20 and lift >= 1.2:
                        fallback_rule = {
                            "antecedent": [sku],
                            "consequent": [cand_item],
                            "support": round(cnt / n_baskets, 4),
                            "confidence": round(conf, 4),
                            "lift": round(lift, 2),
                            "count": cnt,
                            "category": STORE_SKU_CATEGORIES.get(sku, "MUG"),
                        }
                        rule_key = (tuple(sorted(fallback_rule["antecedent"])), tuple(sorted(fallback_rule["consequent"])))
                        if rule_key not in seen:
                            seen.add(rule_key)
                            selected.append(fallback_rule)
                            added_sku += 1
                            if added_sku >= 3:
                                break

    # -----------------------------------------------------------------------
    # TIER 2: Category Quotas (Up to 80 rules per category)
    # -----------------------------------------------------------------------
    target_category_ids = ["BAG", "LUNCH", "HERB", "BAKE", "HEART", "CLOCK", "MUG"]
    cat_rules = defaultdict(list)
    for r in all_rules:
        c = classify_rule(r, catalog)
        if c in target_category_ids:
            cat_rules[c].append(r)

    for cat in target_category_ids:
        # Rank by Lift within category to surface highest affinity patterns
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

    # -----------------------------------------------------------------------
    # TIER 3: Multi-item Antecedent Rules (|A| >= 2, up to 200 rules)
    # -----------------------------------------------------------------------
    multi_ant_rules = [r for r in all_rules if len(r["antecedent"]) >= 2]
    multi_by_cat = defaultdict(list)
    for r in multi_ant_rules:
        multi_by_cat[classify_rule(r, catalog)].append(r)

    tier3_added = 0
    # Balanced pass: cap at 30 rules per category to prevent Herb marker choke
    for cat in target_category_ids + ["OTHER"]:
        r_list = sorted(
            multi_by_cat[cat],
            key=lambda x: (round(x["confidence"] * x["lift"], 4), x["lift"], x["confidence"]),
            reverse=True,
        )
        cat_added = 0
        for r in r_list:
            rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
            if rule_key not in seen:
                seen.add(rule_key)
                r_copy = dict(r)
                r_copy["category"] = classify_rule(r_copy, catalog)
                selected.append(r_copy)
                cat_added += 1
                tier3_added += 1
                if cat_added >= 30 or tier3_added >= 200:
                    break
        if tier3_added >= 200:
            break

    # Fill remainder of Tier 3 if available
    if tier3_added < 200:
        rem_multi = sorted(
            multi_ant_rules,
            key=lambda x: (round(x["confidence"] * x["lift"], 4), x["lift"], x["confidence"]),
            reverse=True,
        )
        for r in rem_multi:
            if tier3_added >= 200:
                break
            rule_key = (tuple(sorted(r["antecedent"])), tuple(sorted(r["consequent"])))
            if rule_key not in seen:
                seen.add(rule_key)
                r_copy = dict(r)
                r_copy["category"] = classify_rule(r_copy, catalog)
                selected.append(r_copy)
                tier3_added += 1

    # -----------------------------------------------------------------------
    # TIER 4: Global High-Lift Fill (up to total_quota)
    # -----------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 9. Summary KPI Builder
# ---------------------------------------------------------------------------
def build_summary(
    n_baskets: int,
    catalog_size: int,
    store_skus: list[str],
    frequent_itemsets: dict[str, list[dict]],
    total_rules_mined: int,
    curated_rules: list[dict],
    min_support: float,
    min_confidence: float,
    min_count: int = 140,
    min_lift: float = 1.2,
) -> dict:
    """Build summary KPI object covering all requirements and backward-compatible aliases."""
    l1_c = len(frequent_itemsets.get("L1", []))
    l2_c = len(frequent_itemsets.get("L2", []))
    l3_c = len(frequent_itemsets.get("L3", []))
    total_itemsets = l1_c + l2_c + l3_c

    max_lift_val = round(max((r.get("lift", 0.0) for r in curated_rules), default=0.0), 2)

    # Calculate store coverage: store SKUs with >= 1 rule where len(antecedent) == 1
    covered_skus = set()
    for r in curated_rules:
        if len(r.get("antecedent", [])) == 1:
            covered_skus.add(r["antecedent"][0])

    store_cov_count = sum(1 for s in store_skus if s in covered_skus)
    store_cov_pct = round((store_cov_count / len(store_skus) * 100.0) if store_skus else 0.0, 1)

    return {
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
        # Defensive aliases
        "min_count": min_count,
        "min_lift": round(min_lift, 2),
        "catalog_count": catalog_size,
        "catalog_rule_coverage_pct": store_cov_pct,
    }


# ---------------------------------------------------------------------------
# 10. Pipeline Orchestrator & Entry Point
# ---------------------------------------------------------------------------
def main(path: str):
    if not os.path.exists(path):
        print(f"Error: Dataset not found at {path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading and cleaning Excel file: {path}...")
    prod_names = defaultdict(Counter)
    prod_prices = defaultdict(list)
    baskets_map = defaultdict(set)

    for row in iter_rows(path):
        inv, stock, desc, qty, dt, price, cust, country = row
        inv = str(inv or "")
        stock = str(stock or "").strip()
        if not inv or inv.startswith("C") or not stock:
            continue
        try:
            qty = int(float(qty or 0))
            price = float(price or 0)
        except (ValueError, TypeError):
            continue
        if qty <= 0 or price <= 0:
            continue
        if stock in NON_PRODUCT or not re.match(r"^\d{5}", stock):
            continue

        baskets_map[inv].add(stock)
        if desc:
            prod_names[stock][desc.strip()] += 1
        prod_prices[stock].append(price)

    raw_catalog = {}
    for stock, counts in prod_names.items():
        name = counts.most_common(1)[0][0]
        prices = prod_prices[stock]
        prices.sort()
        med_price = round(prices[len(prices) // 2], 2) if prices else 2.50
        raw_catalog[stock] = {
            "code": stock,
            "name": name,
            "price": med_price,
        }

    baskets = [b for b in baskets_map.values() if len(b) >= 2]
    n_baskets = len(baskets)
    print(f"Total multi-item baskets: {n_baskets}, Raw catalog items: {len(raw_catalog)}")

    min_count = 140
    min_conf = 0.20
    min_lift = 1.2
    min_support = min_count / n_baskets if n_baskets > 0 else 0.0076

    print(f"Mining rules with Apriori (min_count={min_count}, min_conf={min_conf}, min_lift={min_lift})...")
    all_frequents, all_rules, item_baskets = mine_apriori(
        baskets, min_count=min_count, min_conf=min_conf, min_lift=min_lift
    )
    print(f"Frequent itemsets discovered: {len(all_frequents)}, Valid association rules: {len(all_rules)}")

    print("Extracting frequent itemsets (L1, L2, L3)...")
    frequent_itemsets = extract_frequent_itemsets(all_frequents, n_baskets)
    print(
        f"Itemsets extracted: L1={len(frequent_itemsets['L1'])}, "
        f"L2={len(frequent_itemsets['L2'])}, "
        f"L3={len(frequent_itemsets['L3'])}"
    )

    print("Enriching catalog metadata...")
    catalog = enrich_catalog(raw_catalog, item_baskets, n_baskets)

    print("Extracting combo bundles...")
    combos = extract_combos(all_frequents, n_baskets, catalog, limit=80)

    print("Selecting diversified rules via 4-tier stratified allocation...")
    curated_rules = select_diversified_rules(
        all_rules=all_rules,
        baskets=baskets,
        catalog=catalog,
        item_baskets=item_baskets,
        total_quota=1000,
    )
    print(f"Selected {len(curated_rules)} diversified rules across all categories.")

    print("Building executive summary KPIs...")
    summary = build_summary(
        n_baskets=n_baskets,
        catalog_size=len(catalog),
        store_skus=STORE_SKUS,
        frequent_itemsets=frequent_itemsets,
        total_rules_mined=len(all_rules),
        curated_rules=curated_rules,
        min_support=min_support,
        min_confidence=min_conf,
        min_count=min_count,
        min_lift=min_lift,
    )

    payload = {
        "dataset_name": "UCI Online Retail (Cleaned Baskets)",
        "total_baskets": n_baskets,
        "summary": summary,
        "categories": STORE_CATEGORIES_DEF,
        "store_skus": STORE_SKUS,
        "catalog": catalog,
        "frequent_itemsets": frequent_itemsets,
        "rules": curated_rules,
        "combos": combos,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    file_size_kb = os.path.getsize(OUT_FILE) // 1024
    print(f"Successfully saved rules & catalog to {OUT_FILE} ({file_size_kb} KB)")
    print(f"Store coverage: {summary['store_coverage_pct']}% of {summary['store_products_count']} store products covered.")


if __name__ == "__main__":
    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ucitest/Online Retail.xlsx"
    main(xlsx_path)
