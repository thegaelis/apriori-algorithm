"""Mine association rules from Online Retail dataset using optimized Apriori.

Extracts top products, catalog info, and association rules at multiple min_sup/min_conf thresholds.
Saves to src/data/ecom_rules.json for instant UI querying with zero runtime overhead on Render.
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

def load_shared(z: zipfile.ZipFile) -> list[str]:
    out = []
    for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if el.tag == NS + "si":
            out.append("".join(t.text or "" for t in el.iter(NS + "t")))
            el.clear()
    return out

def iter_rows(path: str):
    with zipfile.ZipFile(path) as z:
        shared = load_shared(z)
        row: dict[str, object] = {}
        for ev, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml"), events=("end",)):
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

def mine_apriori(baskets: list[set[str]], min_count: int, min_conf: float):
    n = len(baskets)
    # 1-itemsets
    item_baskets = defaultdict(set)
    for tid, b in enumerate(baskets):
        for item in b:
            item_baskets[item].add(tid)
    
    L1 = {frozenset([item]): tids for item, tids in item_baskets.items() if len(tids) >= min_count}
    all_frequents = dict(L1)
    current_L = L1
    k = 2
    
    while current_L:
        # Candidate generation (join)
        itemsets = list(current_L.keys())
        candidates = set()
        for i in range(len(itemsets)):
            for j in range(i + 1, len(itemsets)):
                union = itemsets[i] | itemsets[j]
                if len(union) == k:
                    # Apriori prune: check all (k-1) subsets
                    if all(frozenset(sub) in current_L for sub in combinations(union, k - 1)):
                        candidates.add(union)
        
        # Scan / Intersect
        next_L = {}
        for cand in candidates:
            # intersection of tids
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

    # Rule generation
    rules = []
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
                    lift = conf / supp_con if supp_con > 0 else 0
                    rules.append({
                        "antecedent": sorted(ant),
                        "consequent": sorted(con),
                        "support": round(supp_both, 4),
                        "confidence": round(conf, 4),
                        "lift": round(lift, 2),
                        "count": count_both,
                    })
    rules.sort(key=lambda x: (x["lift"], x["confidence"], x["support"]), reverse=True)
    return all_frequents, rules

def main(path: str):
    print("Reading Excel file...")
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

    catalog = {}
    for stock, counts in prod_names.items():
        name = counts.most_common(1)[0][0]
        prices = prod_prices[stock]
        prices.sort()
        med_price = round(prices[len(prices) // 2], 2) if prices else 2.50
        catalog[stock] = {
            "code": stock,
            "name": name,
            "price": med_price,
        }

    baskets = [b for b in baskets_map.values() if len(b) >= 2]
    n_baskets = len(baskets)
    print(f"Total multi-item baskets: {n_baskets}, Catalog items: {len(catalog)}")

    # We mine with min_count = 150 (approx ~0.8% support), min_conf = 0.25 to catch rich real cross-sell patterns
    print("Mining rules with Apriori...")
    freqs, rules = mine_apriori(baskets, min_count=160, min_conf=0.25)
    print(f"Frequent itemsets found: {len(freqs)}, Strong rules found: {len(rules)}")

    # Format frequent pairs for combos/bundles
    combos = []
    for itemset, tids in freqs.items():
        if len(itemset) == 2:
            it = sorted(itemset)
            combos.append({
                "items": it,
                "support": round(len(tids) / n_baskets, 4),
                "count": len(tids),
            })
    combos.sort(key=lambda x: x["count"], reverse=True)

    out = {
        "dataset_name": "UCI Online Retail (Cleaned Baskets)",
        "total_baskets": n_baskets,
        "catalog": catalog,
        "rules": rules[:350],  # keep top 350 most meaningful rules
        "combos": combos[:80],
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Successfully saved rules & catalog to {OUT_FILE} ({os.path.getsize(OUT_FILE) // 1024} KB)")

if __name__ == "__main__":
    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ucitest/Online Retail.xlsx"
    main(xlsx_path)
