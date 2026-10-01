"""Compatibility presentation for the original /api/analyze response.

All candidate generation, support counting and rule evaluation use the shared
engine. This module only adapts its trace to the original educational schema.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from .apriori import (
    Itemset, build_apriori_trace, clean_item, format_itemset, format_rule,
)


def analyze_baskets(
    transactions_input: Iterable[Iterable[str]],
    min_support: float,
    min_confidence: float,
) -> dict[str, Any]:
    """Run full Apriori: C1→L1→Ck→Lk→Rules. Returns educational trace."""
    # --- STEP 1: Clean & normalize input transactions ---
    transactions = [
        frozenset(filter(None, map(clean_item, t)))
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
    frequent_itemsets: list[tuple[Itemset, float, int]] = []

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

    # Adapt the shared mining trace to the original Python/API response schema.
    trace = build_apriori_trace(trans_display, min_support_count, min_confidence)
    scans = {step["k"]: step for step in trace["steps"] if step["type"] == "scan"}
    joins = {step["k"]: step for step in trace["steps"] if step["type"] == "join"}
    prunes = {step["k"]: step for step in trace["steps"] if step["type"] == "prune"}

    current_candidates = [frozenset([item]) for item in all_unique_items]
    level = 1

    while current_candidates:
        candidate_evaluations = []
        current_frequents = []

        for row in scans[level]["rows"]:
            candidate = frozenset(row["c"])
            matched_tids, count, support = row["tids"], row["n"], row["sup"]
            support_map[candidate] = support
            is_frequent = row["keep"]
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
        join = joins.get(next_level)
        prune = prunes.get(next_level)
        if not join or not prune:
            break
        source_pairs = {
            tuple(pair["cand"]): pair for pair in join["pairs"] if pair["ok"]
        }
        join_pairs = []
        pruned_subsets = []
        for row in prune["rows"]:
            pair = source_pairs[tuple(row["c"])]
            missing = [sub["s"] for sub in row["subs"] if not sub["ok"]]
            label = format_itemset(row["c"])
            join_pairs.append({
                "from_pair": f"{format_itemset(pair['l1'])} + {format_itemset(pair['l2'])}",
                "candidate": label,
                "subsets": [format_itemset(sub["s"]) for sub in row["subs"]],
                "missing_subsets": [format_itemset(sub) for sub in missing],
                "passed_prune": row["keep"],
                "action": f"ACCEPTED into C{next_level}" if row["keep"] else "PRUNED",
            })
            if missing:
                pruned_subsets.append({
                    "candidate": label, "missing_subset": format_itemset(missing[0]),
                    "reason": f"Subset {format_itemset(missing[0])} not in L{level}.",
                })
        next_candidates = valid_candidates = [frozenset(c) for c in prune["kept"]]

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
    rules, rule_steps = _format_legacy_rules(trace)

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
        "steps": [
            {"level": step["data"]["level"],
             "candidates": step["data"]["candidates"],
             "next_candidates": step["data"]["frequent_itemsets"]}
            for step in training_steps if step["step_id"].startswith("scan_filter_")
        ],
        "frequent_itemsets": frequent_itemsets,
        "rules": rules,
        "support_map": support_map,
    }


def _format_legacy_rules(trace: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Format already evaluated rules; mining and metrics live in one engine."""
    accepted_rules = []
    rule_evaluations = []
    n = trace["N"]
    min_confidence = trace["minConf"]
    for group in trace["groups"]:
        itemset = frozenset(group["l"])
        for rule in group["rules"]:
            antecedent, consequent = frozenset(rule["s"]), frozenset(rule["b"])
            support, ant_supp, cons_supp = rule["sl"] / n, rule["ss"] / n, rule["sb"] / n
            confidence, lift, is_accepted = rule["conf"], rule["lift"], rule["ok"]
            rule_eval = {
                "rule": format_rule(antecedent, consequent),
                "antecedent": format_itemset(antecedent),
                "consequent": format_itemset(consequent),
                "itemset": format_itemset(itemset),
                "support": support, "support_pct": f"{support:.1%}",
                "antecedent_support_pct": f"{ant_supp:.1%}",
                "consequent_support_pct": f"{cons_supp:.1%}",
                "antecedent_count": rule["ss"],
                "itemset_count": rule["sl"],
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


