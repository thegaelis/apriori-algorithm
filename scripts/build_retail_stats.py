"""Build algorithm-centric dataset statistics for the Groceries POS dataset (Hahsler et al., 2006).

Directly addresses the 3 core Apriori pillars that connect the dataset to the web storefront:
1. Bestsellers (L1): Which items sell the most? What are their exact basket counts and support (%)?
2. Frequent Combos (L2 & L3): Which item pairs/triplets are bought together? Why, and with what counts & support?
3. Product Recommendations (A => B): How do Support, Confidence, and Lift mathematically justify recommending item B when buying item A?

Output: src/data/retail_stats.json (consumed by /stats and /api/retail-stats).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(PROJECT_ROOT, "src", "data", "groceries.csv")
RULES_FILE = os.path.join(PROJECT_ROOT, "src", "data", "ecom_rules.json")
OUT_FILE = os.path.join(PROJECT_ROOT, "src", "data", "retail_stats.json")


def quantiles(sorted_vals: list[float]) -> dict:
    n = len(sorted_vals)
    if not n:
        return {}
    q = lambda p: sorted_vals[min(n - 1, int(p * (n - 1)))]
    mean = sum(sorted_vals) / n
    var = sum((x - mean) ** 2 for x in sorted_vals) / n
    return {
        "min": sorted_vals[0],
        "p25": q(0.25),
        "median": q(0.5),
        "p75": q(0.75),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": sorted_vals[-1],
        "mean": round(mean, 2),
        "std": round(var ** 0.5, 2),
    }


def hist(values: list[int], edges: list[int]) -> dict:
    labels, counts = [], [0] * len(edges)
    for i, e in enumerate(edges):
        if i == len(edges) - 1:
            labels.append(f"{e}+")
        elif edges[i + 1] == e + 1:
            labels.append(f"{e}")
        else:
            labels.append(f"{e}-{edges[i + 1] - 1}")
    for v in values:
        idx = 0
        for i, e in enumerate(edges):
            if v >= e:
                idx = i
        counts[idx] += 1
    return {"labels": labels, "counts": counts}


def main(csv_path: str = DEFAULT_CSV) -> None:
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        baskets = [
            sorted({x.strip() for x in line.strip().split(",") if x.strip()})
            for line in f
            if line.strip()
        ]

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        ecom_data = json.load(f)

    catalog = ecom_data.get("catalog", {})
    frequents = ecom_data.get("frequent_itemsets", {})
    rules = ecom_data.get("rules", [])

    n_tx = len(baskets)
    total_item_occurrences = sum(len(b) for b in baskets)
    item_counts = Counter(item for b in baskets for item in b)
    sizes = sorted(len(b) for b in baskets)
    multi_item_baskets = sum(1 for s in sizes if s >= 2)
    single_item_baskets = sum(1 for s in sizes if s == 1)

    # Support curve across thresholds
    item_sup_list = sorted(item_counts.values(), reverse=True)
    sup_curve = []
    for pct in (0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0):
        thr = n_tx * pct / 100.0
        sup_curve.append({
            "min_sup_pct": pct,
            "min_count": round(thr, 1),
            "frequent_items": sum(1 for c in item_sup_list if c >= thr),
        })

    # Pillar 1: Top Bestsellers (L1)
    top_bestsellers = []
    for item, cnt in item_counts.most_common(20):
        cat_info = catalog.get(item, {})
        supp_pct = round(100.0 * cnt / n_tx, 2)
        top_bestsellers.append({
            "code": item,
            "name": item,
            "icon": cat_info.get("icon", "🛒"),
            "category": cat_info.get("category", "OTHER"),
            "price": cat_info.get("price", 1.99),
            "baskets": cnt,
            "support": round(cnt / n_tx, 4),
            "support_pct": supp_pct,
        })

    # Pillar 2: Top Frequent Combos (L2 Pairs & L3 Triplets)
    top_l2_combos = []
    for entry in frequents.get("L2", [])[:20]:
        items = entry["items"]
        cnt = entry["count"]
        supp_pct = round(100.0 * cnt / n_tx, 2)
        c_a = item_counts[items[0]]
        c_b = item_counts[items[1]]
        expected_random_cnt = round((c_a * c_b) / n_tx, 1)
        co_lift = round(cnt / expected_random_cnt, 2) if expected_random_cnt > 0 else 1.0
        top_l2_combos.append({
            "items": items,
            "k": 2,
            "count": cnt,
            "support": entry["support"],
            "support_pct": supp_pct,
            "item_a_count": c_a,
            "item_a_support_pct": round(100.0 * c_a / n_tx, 2),
            "item_b_count": c_b,
            "item_b_support_pct": round(100.0 * c_b / n_tx, 2),
            "expected_random_count": expected_random_cnt,
            "cooccurrence_lift": co_lift,
        })

    top_l3_combos = []
    for entry in frequents.get("L3", [])[:15]:
        items = entry["items"]
        cnt = entry["count"]
        supp_pct = round(100.0 * cnt / n_tx, 2)
        top_l3_combos.append({
            "items": items,
            "k": 3,
            "count": cnt,
            "support": entry["support"],
            "support_pct": supp_pct,
        })

    # Pillar 3: Highlighted Association Rules (A => B) explaining storefront recommendations
    # Calculate exact antecedent & consequent basket counts for transparent formula proof
    baskets_sets = [set(b) for b in baskets]
    sorted_rules = sorted(
        rules,
        key=lambda r: (round(r["confidence"] * r["lift"], 4), r["lift"], r["count"]),
        reverse=True,
    )
    top_recommendation_rules = []
    seen_targets = Counter()
    for r in sorted_rules:
        ant = r["antecedent"]
        con = r["consequent"]
        target_key = con[0]
        if seen_targets[target_key] >= 4:
            continue
        seen_targets[target_key] += 1

        ant_set = set(ant)
        con_set = set(con)
        ant_cnt = sum(1 for b in baskets_sets if ant_set.issubset(b))
        con_cnt = sum(1 for b in baskets_sets if con_set.issubset(b))
        both_cnt = r["count"]

        top_recommendation_rules.append({
            "antecedent": ant,
            "consequent": con,
            "count": both_cnt,
            "support": r["support"],
            "support_pct": round(r["support"] * 100.0, 2),
            "antecedent_count": ant_cnt,
            "antecedent_support_pct": round(100.0 * ant_cnt / n_tx, 2),
            "consequent_count": con_cnt,
            "consequent_support_pct": round(100.0 * con_cnt / n_tx, 2),
            "confidence": r["confidence"],
            "confidence_pct": round(r["confidence"] * 100.0, 1),
            "lift": r["lift"],
            "reason": r.get("reason", ""),
        })
        if len(top_recommendation_rules) >= 24:
            break

    out = {
        "source": "Groceries POS Dataset — Michael Hahsler, Kurt Hornik, Thomas Reutterer (2006), WU Vienna / R arules",
        "url": "https://cran.r-project.org/web/packages/arules/index.html",
        "overview": {
            "transactions": n_tx,
            "multi_item_baskets": multi_item_baskets,
            "multi_item_baskets_pct": round(100.0 * multi_item_baskets / n_tx, 2),
            "single_item_baskets": single_item_baskets,
            "single_item_baskets_pct": round(100.0 * single_item_baskets / n_tx, 2),
            "total_item_purchases": total_item_occurrences,
            "distinct_items": len(item_counts),
            "store_curated_items": len(ecom_data.get("store_skus", [])),
            "avg_basket_size": round(total_item_occurrences / n_tx, 2),
            "l1_count": len(frequents.get("L1", [])),
            "l2_count": len(frequents.get("L2", [])),
            "l3_count": len(frequents.get("L3", [])),
            "total_frequent_itemsets": (
                len(frequents.get("L1", []))
                + len(frequents.get("L2", []))
                + len(frequents.get("L3", []))
            ),
            "curated_rules_count": len(rules),
            "min_support_count": 30,
            "min_support_pct": round(100.0 * 30 / n_tx, 2),
            "min_confidence_pct": 15.0,
            "min_lift": 1.15,
            "max_lift": ecom_data.get("summary", {}).get("max_lift", 4.81),
        },
        "basket": {
            "clean_transactions": n_tx,
            "clean_rows": total_item_occurrences,
            "distinct_items": len(item_counts),
            "size": quantiles([float(x) for x in sizes]),
            "size_hist": hist(sizes, [1, 2, 3, 4, 5, 6, 8, 11, 16, 21]),
            "single_item_baskets_pct": round(100.0 * single_item_baskets / n_tx, 2),
            "multi_item_baskets": multi_item_baskets,
            "density_pct": round(100.0 * total_item_occurrences / (n_tx * len(item_counts)), 2),
            "support_curve": sup_curve,
        },
        "top_products_by_baskets": top_bestsellers,
        "top_l2_combos": top_l2_combos,
        "top_l3_combos": top_l3_combos,
        "top_recommendation_rules": top_recommendation_rules,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"Wrote {OUT_FILE} ({os.path.getsize(OUT_FILE)//1024} KB)")


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    main(csv_arg)
