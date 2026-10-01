from __future__ import annotations
from collections.abc import Iterable
from itertools import combinations
import re
from typing import Any

# ======================================================================
# APRIORI ALGORITHM — STEP-BY-STEP OVERVIEW
# ======================================================================
# 1. C1: All unique 1-itemsets from transactions.
# 2. L1: Keep items with support >= min_support (prune rest).
# 3. Ck (k>1): Join L(k-1) pairs that share (k-2) items.
# 4. Prune Ck: Drop candidates with any (k-1)-subset missing from L(k-1).
# 5. Lk: Scan transactions, keep frequent itemsets.
# 6. Repeat 3-5 until no new candidates.
# 7. Rules: For each frequent itemset (size>=2), split into A -> B.
#    Confidence = Support(A∪B) / Support(A). Keep if >= min_confidence.
#    Lift = Confidence / Support(B). Lift > 1 => positive correlation.
# ======================================================================

Transaction = frozenset[str]
Itemset = frozenset[str]


def clean_item(value: str) -> str:
    return value.strip().lower()


def parse_baskets(text: str) -> list[Transaction]:
    """Parse multiline basket text into normalized frozenset transactions."""
    baskets = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        items = [clean_item(p) for p in re.split(r"[,;|\t]+", line)]
        filtered = [i for i in items if i]
        if filtered:
            baskets.append(frozenset(filtered))
    return baskets


def format_itemset(itemset: Iterable[str]) -> str:
    return "{" + ", ".join(sorted(itemset)) + "}"


def format_rule(antecedent: Iterable[str], consequent: Iterable[str]) -> str:
    return f"{format_itemset(antecedent)} -> {format_itemset(consequent)}"


def analyze_baskets(
    transactions_input: Iterable[Iterable[str]], min_support: float, min_confidence: float
) -> dict[str, Any]:
    """Compatibility entry point backed by the shared trace engine."""
    from .legacy import analyze_baskets as format_analysis

    return format_analysis(transactions_input, min_support, min_confidence)


# ------------------------------------------------------------------
# Shared mining engine: JSON-ready trace for both HTTP endpoints
# ------------------------------------------------------------------

def natural_sort_key(value: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", value))


def _itemset_key(itemset: list[str]) -> str:
    return "|".join(itemset)


def build_apriori_trace(
    transactions: list[dict], min_count: int, min_confidence: float
) -> dict[str, Any]:
    n = len(transactions)
    items = sorted({item for t in transactions for item in t["items"]}, key=natural_sort_key)
    tsets = [set(t["items"]) for t in transactions]

    def sort_itemsets(itemsets: list[list[str]]) -> list[list[str]]:
        return sorted(itemsets, key=lambda c: tuple(natural_sort_key(x) for x in c))

    count: dict[str, int] = {}
    steps: list[dict] = []
    levels: list[dict] = []
    l_all: list[list[list[str]]] = []
    pruned: set[str] = set()

    steps.append({"type": "setup"})
    k = 1
    candidates = [[item] for item in items]
    stop = None
    last_dropped = []

    while True:
        lvl = {"k": k, "joinCount": None, "pruneCount": None, "L": []}
        if k > 1:
            prev = l_all[k - 2]
            pairs = []
            cands = []
            for i in range(len(prev)):
                for j in range(i + 1, len(prev)):
                    l1, l2 = prev[i], prev[j]
                    ok = l1[: k - 2] == l2[: k - 2]
                    cand = sorted(set(l1) | {l2[k - 2]}, key=natural_sort_key) if ok else None
                    pairs.append({"l1": l1, "l2": l2, "ok": ok, "cand": cand})
                    if ok and cand is not None:
                        cands.append(cand)
            cands = sort_itemsets(cands)
            lvl["joinCount"] = len(cands)
            steps.append({"type": "join", "k": k, "pairs": pairs, "cands": cands, "prevL": prev, "dropped": last_dropped})
            if not cands:
                stop = {"type": "end", "k": k, "reason": "join"}
                levels.append(lvl)
                break
            prev_set = {_itemset_key(p) for p in prev}
            rows = []
            for c in cands:
                subs = []
                for idx in range(len(c) - 1, -1, -1):
                    s = [x for pos, x in enumerate(c) if pos != idx]
                    subs.append({"s": s, "ok": _itemset_key(s) in prev_set})
                keep = all(sub["ok"] for sub in subs)
                if not keep:
                    pruned.add(_itemset_key(c))
                rows.append({"c": c, "subs": subs, "keep": keep})
            kept = [r["c"] for r in rows if r["keep"]]
            lvl["pruneCount"] = len(kept)
            steps.append({"type": "prune", "k": k, "rows": rows, "kept": kept, "prunedN": len(rows) - len(kept)})
            if not kept:
                stop = {"type": "end", "k": k, "reason": "prune"}
                levels.append(lvl)
                break
            candidates = kept
        else:
            lvl["joinCount"] = len(candidates)
            lvl["pruneCount"] = len(candidates)

        rows = []
        for c in candidates:
            c_set = set(c)
            tids = [transactions[i]["tid"] for i in range(n) if c_set.issubset(tsets[i])]
            cnt = len(tids)
            count[_itemset_key(c)] = cnt
            rows.append({"c": c, "tids": tids, "n": cnt, "sup": cnt / n, "keep": cnt >= min_count})
        l_k = [r["c"] for r in rows if r["keep"]]
        last_dropped = [r["c"] for r in rows if not r["keep"]]
        lvl["L"] = l_k
        levels.append(lvl)
        l_all.append(l_k)
        steps.append({"type": "scan", "k": k, "rows": rows, "L": l_k, "scanNo": k})
        if not l_k:
            stop = {"type": "end", "k": k, "reason": "L"}
            break
        if len(l_k) == 1:
            k += 1
            steps.append({"type": "join", "k": k, "pairs": [], "cands": [], "prevL": l_k, "dropped": last_dropped})
            stop = {"type": "end", "k": k, "reason": "join"}
            break
        k += 1

    steps.append(stop)
    freq = [itemset for level_items in l_all for itemset in level_items]
    groups = []
    strong = 0
    for l in freq:
        if len(l) < 2:
            continue
        sl = count[_itemset_key(l)]
        rules = []
        for size in range(len(l) - 1, 0, -1):
            for s_tuple in combinations(l, size):
                s = list(s_tuple)
                b = [x for x in l if x not in s]
                ss = count[_itemset_key(s)]
                sb = count[_itemset_key(b)]
                # The legacy API permits a zero support threshold.
                conf = sl / ss if ss else 0.0
                lift = conf / (sb / n) if sb else 0.0
                ok = conf >= min_confidence - 1e-9
                if ok:
                    strong += 1
                rules.append({"s": s, "b": b, "sl": sl, "ss": ss, "sb": sb, "conf": conf, "lift": lift, "ok": ok})
        groups.append({"l": l, "sl": sl, "rules": rules})
    steps.append({"type": "rules", "groups": groups, "strong": strong})
    steps.append({"type": "summary"})
    scans = sum(1 for s in steps if s["type"] == "scan")
    return {
        "N": n, "items": items, "count": count, "steps": steps,
        "levels": levels, "Lall": l_all, "freq": freq,
        "groups": groups, "strong": strong, "scans": scans,
        "pruned": sorted(pruned), "minCount": min_count, "minConf": min_confidence,
    }
