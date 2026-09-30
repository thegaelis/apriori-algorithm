from __future__ import annotations
from collections.abc import Iterable
from itertools import combinations
import math, re
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
    transactions_input: Iterable[Iterable[str]],
    min_support: float,
    min_confidence: float,
) -> dict[str, Any]:
    """Run full Apriori: C1→L1→Ck→Lk→Rules. Returns educational trace."""
    # --- STEP 1: Clean & normalize input transactions ---
    transactions = [
        frozenset(clean_item(i) for i in t if clean_item(i))
        for t in transactions_input
    ]
    transactions = [t for t in transactions if t]
    n_trans = len(transactions)
    min_support_count = math.ceil(min_support * n_trans) if n_trans > 0 else 0

    if n_trans == 0:
        return {
            "transaction_count": 0, "min_support": min_support,
            "min_confidence": min_confidence, "min_support_count": 0,
            "transactions": [], "all_unique_items": [],
            "training_steps": [], "steps": [],
            "frequent_itemsets": [], "rules": [], "support_map": {},
        }

    all_unique_items = sorted({item for t in transactions for item in t})
    trans_display = [
        {"tid": f"T{i+1}", "items": sorted(t), "formatted": format_itemset(t)}
        for i, t in enumerate(transactions)
    ]

    training_steps: list[dict] = []
    support_map: dict[Itemset, float] = {}
    count_map: dict[Itemset, int] = {}
    frequent_itemsets: list[tuple[Itemset, float, int]] = []
    legacy_steps: list[dict] = []

    # Setup step
    training_steps.append({
        "step_number": 1, "step_id": "setup", "phase": "Problem Setup",
        "title": "Dataset & Mining Parameters",
        "concept": "Market Basket Analysis Fundamentals",
        "explanation": (
            f"We have {n_trans} baskets and {len(all_unique_items)} distinct items. "
            f"Min Support = {min_support:.0%} => at least {min_support_count} baskets. "
            f"Min Confidence = {min_confidence:.0%}."
        ),
        "formula": {
            "name": "Minimum Support Count Threshold",
            "expression": r"minsup\_count = \lceil minsup \times N \rceil",
            "calculation": f"ceil({min_support:.2f} × {n_trans}) = {min_support_count}",
        },
        "data": {
            "transactions": trans_display, "unique_items": all_unique_items,
            "total_transactions": n_trans, "min_support": min_support,
            "min_support_count": min_support_count, "min_confidence": min_confidence,
        },
        "key_takeaway": f"Any itemset in < {min_support_count} baskets is pruned.",
    })

    # --- STEP 2-6: Iterative mining (Ck → Lk) ---
    current_candidates = [frozenset([item]) for item in all_unique_items]
    level = 1

    while current_candidates:
        candidate_evaluations = []
        current_frequents = []

        for candidate in sorted(current_candidates, key=lambda s: sorted(s)):
            matched_tids = [f"T{i+1}" for i, t in enumerate(transactions) if candidate.issubset(t)]
            count = len(matched_tids)
            support = count / n_trans
            support_map[candidate] = support
            count_map[candidate] = count
            is_frequent = count >= min_support_count
            candidate_evaluations.append({
                "items": sorted(candidate), "label": format_itemset(candidate),
                "matched_tids": matched_tids, "count": count,
                "support": support, "support_pct": f"{support:.1%}",
                "is_frequent": is_frequent,
                "decision": f"KEEP in L{level}" if is_frequent else "PRUNE",
                "reason": (
                    f"Count {count} >= {min_support_count}" if is_frequent
                    else f"Count {count} < {min_support_count}"
                ),
            })
            if is_frequent:
                current_frequents.append(candidate)
                frequent_itemsets.append((candidate, support, count))

        legacy_steps.append({
            "level": level,
            "candidates": candidate_evaluations,
            "next_candidates": [format_itemset(i) for i in current_frequents],
        })

        kept = len(current_frequents)
        pruned = len(current_candidates) - kept
        level_title = f"Scan & Filter {level}-Itemsets (C{level} → L{level})"
        training_steps.append({
            "step_number": len(training_steps) + 1,
            "step_id": f"scan_filter_L{level}",
            "phase": f"Level {level} Support Counting",
            "title": level_title,
            "concept": f"Support counting for C{level} → L{level}",
            "explanation": (
                f"Scanned {n_trans} baskets. {kept} kept, {pruned} pruned."
            ),
            "formula": {
                "name": f"Support of {level}-itemset",
                "expression": r"\text{Support}(X) = \frac{\text{count}(X)}{N}",
                "calculation": f"count(X) / {n_trans} >= {min_support:.0%}",
            },
            "data": {
                "level": level, "candidates": candidate_evaluations,
                "candidates_count": len(current_candidates),
                "frequent_count": kept, "pruned_count": pruned,
                "frequent_itemsets": [format_itemset(i) for i in current_frequents],
            },
            "key_takeaway": (
                "Downward-closure: infrequent items cannot be in frequent sets."
                if level == 1 else f"Only L{level} forms C{level+1}."
            ),
        })

        if not current_frequents:
            break

        next_level = level + 1
        next_candidates, join_trace = generate_candidates_with_trace(
            current_frequents, next_level, set(current_frequents)
        )
        if not next_candidates and not join_trace.get("joined_pairs"):
            break

        join_pairs = join_trace.get("joined_pairs", [])
        pruned_subsets = join_trace.get("pruned_by_apriori", [])
        valid_candidates = join_trace.get("valid_candidates", [])

        training_steps.append({
            "step_number": len(training_steps) + 1,
            "step_id": f"candidate_gen_C{next_level}",
            "phase": f"Candidate Generation C{next_level}",
            "title": f"Candidate Generation (L{level} → C{next_level})",
            "concept": "Apriori Join + Prune",
            "explanation": (
                f"Join pairs from L{level} that share {level-1} items, then prune "
                f"candidates missing any {level}-subset from L{level}."
            ),
            "formula": {
                "name": "Apriori Pruning Property",
                "expression": r"\forall s \subset c, |s|=k-1: s \in L_{k-1}",
                "calculation": f"Every {level}-subset must be in L{level}",
            },
            "data": {
                "level": next_level,
                "source_frequent": [format_itemset(i) for i in current_frequents],
                "joined_combinations": join_pairs,
                "pruned_by_apriori": pruned_subsets,
                "final_candidates": [format_itemset(i) for i in valid_candidates],
                "final_candidates_count": len(valid_candidates),
            },
            "key_takeaway": (
                f"Only {len(valid_candidates)} candidates to scan for C{next_level}."
            ),
        })

        if not next_candidates:
            break
        current_candidates = next_candidates
        level += 1

    # --- STEP 7: Generate association rules from frequent itemsets ---
    rules, rule_steps = generate_rules_with_trace(
        transactions, frequent_itemsets, support_map, count_map, min_confidence
    )

    training_steps.append({
        "step_number": len(training_steps) + 1,
        "step_id": "rule_generation",
        "phase": "Association Rule Mining",
        "title": "Deriving Association Rules (A → B)",
        "concept": "Confidence & Lift",
        "explanation": (
            f"From frequent itemsets (size ≥ 2), generate A → B rules. "
            f"Confidence = Support(A∪B) / Support(A). Keep if ≥ {min_confidence:.0%}."
        ),
        "formula": {
            "name": "Confidence & Lift",
            "expression": r"\text{Conf}=\frac{S(A\cup B)}{S(A)}, \text{Lift}=\frac{\text{Conf}}{S(B)}",
            "calculation": f"Accept if Conf ≥ {min_confidence:.0%}",
        },
        "data": {
            "all_evaluated_rules": rule_steps,
            "accepted_rules_count": len(rules),
            "total_rules_tested": len(rule_steps),
        },
        "key_takeaway": f"{len(rules)} rule(s) met confidence ≥ {min_confidence:.0%}.",
    })

    frequent_itemsets.sort(key=lambda r: (len(r[0]), sorted(r[0])))

    training_steps.append({
        "step_number": len(training_steps) + 1,
        "step_id": "summary",
        "phase": "Summary",
        "title": "Results & Business Action",
        "concept": "Applying Market Basket Analysis",
        "explanation": (
            f"Mined {len(frequent_itemsets)} frequent itemsets and {len(rules)} rules."
        ),
        "formula": {
            "name": "Summary Metrics",
            "expression": r"\text{Itemsets} \implies \text{Rules} \implies \text{Strategy}",
            "calculation": f"{len(frequent_itemsets)} itemsets, {len(rules)} rules",
        },
        "data": {
            "frequent_itemsets": [
                {"itemset": format_itemset(i), "size": len(i),
                 "support": f"{s:.1%}", "count": c}
                for i, s, c in frequent_itemsets
            ],
            "rules": [
                {"rule": format_rule(r["antecedent"], r["consequent"]),
                 "antecedent": format_itemset(r["antecedent"]),
                 "consequent": format_itemset(r["consequent"]),
                 "support": f"{r['support']:.1%}",
                 "confidence": f"{r['confidence']:.1%}",
                 "lift": f"{r['lift']:.2f}",
                 "interpretation": (
                     "Strong (Lift > 1.2)" if r["lift"] > 1.2
                     else ("Moderate" if r["lift"] >= 1.0 else "Weak/negative")
                 )}
                for r in rules
            ],
        },
        "key_takeaway": "Full Apriori workflow completed.",
    })

    return {
        "transaction_count": n_trans,
        "min_support": min_support,
        "min_confidence": min_confidence,
        "min_support_count": min_support_count,
        "transactions": trans_display,
        "all_unique_items": all_unique_items,
        "training_steps": training_steps,
        "steps": legacy_steps,
        "frequent_itemsets": frequent_itemsets,
        "rules": rules,
        "support_map": support_map,
    }


def generate_candidates_with_trace(
    frequents: list[Itemset], size: int, frequent_lookup: set[Itemset]
) -> tuple[list[Itemset], dict[str, Any]]:
    joined_pairs = []
    pruned_by_apriori = []
    valid_candidates: set[Itemset] = set()
    sorted_frequents = [tuple(sorted(s)) for s in frequents]

    for left, right in combinations(sorted_frequents, 2):
        candidate = frozenset(left).union(right)
        if len(candidate) != size:
            continue
        label = format_itemset(candidate)
        if any(c["candidate"] == label for c in joined_pairs):
            continue
        subsets = [frozenset(s) for s in combinations(candidate, size - 1)]
        missing = [s for s in subsets if s not in frequent_lookup]
        is_valid = len(missing) == 0
        joined_pairs.append({
            "from_pair": f"{format_itemset(left)} + {format_itemset(right)}",
            "candidate": label,
            "subsets": [format_itemset(s) for s in subsets],
            "missing_subsets": [format_itemset(s) for s in missing],
            "passed_prune": is_valid,
            "action": f"ACCEPTED into C{size}" if is_valid else "PRUNED",
        })
        if is_valid:
            valid_candidates.add(candidate)
        else:
            pruned_by_apriori.append({
                "candidate": label,
                "missing_subset": format_itemset(missing[0]) if missing else "",
                "reason": f"Subset {format_itemset(missing[0])} not in L{size-1}.",
            })
    sorted_valid = sorted(valid_candidates, key=lambda v: tuple(sorted(v)))
    return sorted_valid, {
        "joined_pairs": joined_pairs,
        "pruned_by_apriori": pruned_by_apriori,
        "valid_candidates": sorted_valid,
    }


def generate_rules_with_trace(
    transactions: list[Transaction],
    frequent_itemsets: list[tuple[Itemset, float, int]],
    support_map: dict[Itemset, float],
    count_map: dict[Itemset, int],
    min_confidence: float,
) -> tuple[list[dict], list[dict]]:
    accepted_rules = []
    rule_evaluations = []
    for itemset, support, _ in frequent_itemsets:
        if len(itemset) < 2:
            continue
        sorted_items = tuple(sorted(itemset))
        for size in range(1, len(sorted_items)):
            for antecedent_items in combinations(sorted_items, size):
                antecedent = frozenset(antecedent_items)
                consequent = itemset.difference(antecedent)
                if antecedent not in support_map or consequent not in support_map:
                    continue
                ant_supp = support_map[antecedent]
                cons_supp = support_map[consequent]
                confidence = support / ant_supp if ant_supp > 0 else 0.0
                is_accepted = confidence >= min_confidence
                lift = confidence / cons_supp if cons_supp > 0 else 0.0
                rule_eval = {
                    "rule": format_rule(antecedent, consequent),
                    "antecedent": format_itemset(antecedent),
                    "consequent": format_itemset(consequent),
                    "itemset": format_itemset(itemset),
                    "support": support, "support_pct": f"{support:.1%}",
                    "antecedent_support_pct": f"{ant_supp:.1%}",
                    "consequent_support_pct": f"{cons_supp:.1%}",
                    "antecedent_count": count_map.get(antecedent, 0),
                    "itemset_count": count_map.get(itemset, 0),
                    "confidence": confidence, "confidence_pct": f"{confidence:.1%}",
                    "lift": lift, "lift_str": f"{lift:.2f}",
                    "is_accepted": is_accepted,
                    "calculation_formula": (
                        f"Conf = {support:.1%} / {ant_supp:.1%} = {confidence:.1%}"
                    ),
                    "lift_formula": (
                        f"Lift = {confidence:.1%} / {cons_supp:.1%} = {lift:.2f}"
                    ),
                    "decision": (
                        f"ACCEPTED ({confidence:.1%} ≥ {min_confidence:.0%})"
                        if is_accepted else f"REJECTED ({confidence:.1%} < {min_confidence:.0%})"
                    ),
                }
                rule_evaluations.append(rule_eval)
                if is_accepted:
                    accepted_rules.append({
                        "antecedent": antecedent, "consequent": consequent,
                        "support": support, "confidence": confidence, "lift": lift,
                        "rule_eval": rule_eval,
                    })
    accepted_rules.sort(key=lambda r: (-r["confidence"], -r["lift"], format_rule(r["antecedent"], r["consequent"])))
    return accepted_rules, rule_evaluations


# ------------------------------------------------------------------
# Web-trace pipeline (compact, same algorithm, JSON-ready)
# ------------------------------------------------------------------

def natural_sort_key(value: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", value))


def parse_named_baskets(text: str) -> list[dict]:
    transactions = []
    auto = 1
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tid = None
        m = re.match(r"^([^:,;|\t]+):\s*(.*)$", line)
        if m:
            tid = m.group(1).strip()
            line = m.group(2)
        seen = set()
        items = []
        for part in re.split(r"[,;|\t]+", line):
            item = part.strip()
            if item and item not in seen:
                seen.add(item)
                items.append(item)
        if not items:
            continue
        items.sort(key=natural_sort_key)
        transactions.append({"tid": tid or f"T{auto}", "items": items})
        auto += 1
    return transactions


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
                conf = sl / ss
                lift = conf / (sb / n)
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
