from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations
import math
import re
from typing import Any

Transaction = frozenset[str]
Itemset = frozenset[str]

# =============================================================================
# APRIORI ALGORITHM OVERVIEW (Correct Theoretical Flow)
# =============================================================================
# 1) Problem Setup: Given N transactions, min_support threshold, and min_confidence threshold.
# 2) Level 1 Candidates (C1): Form all unique 1-itemsets.
# 3) Support Counting & Prune (C1 -> L1): Scan transactions to compute support count.
#    Keep items with Support >= min_support.
# 4) Level k Candidate Generation (Lk-1 -> Ck):
#    - Join: Join frequent (k-1)-itemsets that share k-2 items.
#    - Prune (Apriori Property): Any candidate whose (k-1)-subset is NOT in Lk-1 is pruned immediately.
# 5) Support Counting & Prune (Ck -> Lk): Scan transactions, keep itemsets with Support >= min_support.
# 6) Repeat steps 4-5 until no more candidates can be generated.
# 7) Association Rule Generation (Lk -> Rules): For every frequent itemset of size >= 2:
#    Split into non-empty antecedent A and consequent B.
#    Confidence(A -> B) = Support(A U B) / Support(A).
#    Keep rules with Confidence >= min_confidence.
#    Lift(A -> B) = Confidence(A -> B) / Support(B).
# =============================================================================


def clean_item(value: str) -> str:
    """Normalize an item token by stripping whitespace and converting to lowercase."""
    return value.strip().lower()


def parse_baskets(text: str) -> list[Transaction]:
    """Parse multiline basket text into normalized frozenset transactions."""
    baskets: list[Transaction] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        items = [clean_item(part) for part in re.split(r"[,;|\t]+", line)]
        filtered = [item for item in items if item]
        if filtered:
            baskets.append(frozenset(filtered))
    return baskets


def format_itemset(itemset: Iterable[str]) -> str:
    """Format an itemset into mathematical notation: {item1, item2}."""
    return "{" + ", ".join(sorted(itemset)) + "}"


def format_rule(antecedent: Iterable[str], consequent: Iterable[str]) -> str:
    """Format an association rule A -> B."""
    return f"{format_itemset(antecedent)} -> {format_itemset(consequent)}"


def analyze_baskets(
    transactions_input: Iterable[Iterable[str]],
    min_support: float,
    min_confidence: float,
) -> dict[str, Any]:
    """
    Execute Apriori algorithm and generate an exhaustive, step-by-step
    pedagogical training trace designed for learners.
    """
    transactions: list[Transaction] = [
        frozenset(clean_item(item) for item in t if clean_item(item))
        for t in transactions_input
    ]
    transactions = [t for t in transactions if t]

    n_trans = len(transactions)
    min_support_count = math.ceil(min_support * n_trans) if n_trans > 0 else 0

    if n_trans == 0:
        return {
            "transaction_count": 0,
            "min_support": min_support,
            "min_confidence": min_confidence,
            "min_support_count": 0,
            "transactions": [],
            "all_unique_items": [],
            "training_steps": [],
            "steps": [],
            "frequent_itemsets": [],
            "rules": [],
            "support_map": {},
        }

    all_unique_items = sorted({item for t in transactions for item in t})

    trans_display = [
        {
            "tid": f"T{idx + 1}",
            "items": sorted(list(t)),
            "formatted": format_itemset(t),
        }
        for idx, t in enumerate(transactions)
    ]

    training_steps: list[dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # STEP 1: Problem Setup & Dataset Inspection
    # -------------------------------------------------------------------------
    training_steps.append({
        "step_number": 1,
        "step_id": "setup",
        "phase": "Problem Setup",
        "title": "Dataset & Mining Parameters",
        "concept": "Market Basket Analysis Fundamentals",
        "explanation": (
            f"We have {n_trans} customer grocery baskets and {len(all_unique_items)} distinct items. "
            f"With Minimum Support = {min_support:.0%}, an itemset must appear in at least "
            f"{min_support_count} out of {n_trans} baskets ({min_support_count}/{n_trans} = {min_support_count / n_trans:.1%}) "
            f"to be considered frequent. Minimum Confidence is set to {min_confidence:.0%}."
        ),
        "formula": {
            "name": "Minimum Support Count Threshold",
            "expression": r"minsup\_count = \lceil minsup \times N \rceil",
            "calculation": f"ceil({min_support:.2f} × {n_trans}) = {min_support_count} baskets",
        },
        "data": {
            "transactions": trans_display,
            "unique_items": all_unique_items,
            "total_transactions": n_trans,
            "min_support": min_support,
            "min_support_count": min_support_count,
            "min_confidence": min_confidence,
        },
        "key_takeaway": (
            f"Any item or combination appearing in fewer than {min_support_count} baskets will be pruned immediately."
        ),
    })

    support_map: dict[Itemset, float] = {}
    count_map: dict[Itemset, int] = {}
    frequent_itemsets: list[tuple[Itemset, float, int]] = []
    legacy_steps: list[dict[str, Any]] = []

    current_candidates = [frozenset([item]) for item in all_unique_items]
    level = 1

    # -------------------------------------------------------------------------
    # ITERATIVE MINING (Levels 1, 2, 3...)
    # -------------------------------------------------------------------------
    while current_candidates:
        candidate_evaluations: list[dict[str, Any]] = []
        current_frequents: list[Itemset] = []

        # Count support for each candidate in transactions
        for candidate in sorted(current_candidates, key=lambda s: sorted(s)):
            matched_tids = [
                f"T{i + 1}"
                for i, t in enumerate(transactions)
                if candidate.issubset(t)
            ]
            count = len(matched_tids)
            support = count / n_trans
            support_map[candidate] = support
            count_map[candidate] = count

            is_frequent = count >= min_support_count

            candidate_evaluations.append({
                "items": sorted(list(candidate)),
                "label": format_itemset(candidate),
                "matched_tids": matched_tids,
                "count": count,
                "support": support,
                "support_pct": f"{support:.1%}",
                "is_frequent": is_frequent,
                "decision": f"KEEP in L{level}" if is_frequent else "PRUNE (Infrequent)",
                "reason": (
                    f"Count {count} >= {min_support_count} ({support:.1%} >= {min_support:.0%})"
                    if is_frequent
                    else f"Count {count} < {min_support_count} ({support:.1%} < {min_support:.0%})"
                ),
            })

            if is_frequent:
                current_frequents.append(candidate)
                frequent_itemsets.append((candidate, support, count))

        legacy_steps.append({
            "level": level,
            "candidates": candidate_evaluations,
            "next_candidates": [format_itemset(itemset) for itemset in current_frequents],
        })

        # Step: Scan & Filter for Level k
        step_num = len(training_steps) + 1
        kept_count = len(current_frequents)
        pruned_count = len(current_candidates) - kept_count

        level_title = (
            f"Scan & Filter 1-Itemsets (C1 → L1)"
            if level == 1
            else f"Scan & Filter {level}-Itemsets (C{level} → L{level})"
        )

        level_explanation = (
            f"We scanned all {n_trans} baskets to count how many times each candidate appeared. "
            f"Out of {len(current_candidates)} candidate(s) in C{level}, "
            f"{kept_count} satisfied the minimum support threshold (>= {min_support_count} baskets) and are retained in L{level}. "
            f"{pruned_count} candidate(s) were pruned."
        )

        takeaway = (
            "Apriori Downward-Closure Principle: If an individual item is infrequent, ANY larger set containing it will also be infrequent!"
            if level == 1
            else f"Only the {kept_count} frequent itemset(s) in L{level} are permitted to form candidates for level {level + 1}."
        )

        training_steps.append({
            "step_number": step_num,
            "step_id": f"scan_filter_L{level}",
            "phase": f"Level {level} Support Counting & Filtering",
            "title": level_title,
            "concept": f"Support Counting for Candidate Set C{level} and Pruning to L{level}",
            "explanation": level_explanation,
            "formula": {
                "name": f"Support of {level}-itemset X",
                "expression": r"\text{Support}(X) = \frac{\text{count}(X)}{N}",
                "calculation": f"count(X) / {n_trans} >= {min_support:.0%}",
            },
            "data": {
                "level": level,
                "candidates": candidate_evaluations,
                "candidates_count": len(current_candidates),
                "frequent_count": kept_count,
                "pruned_count": pruned_count,
                "frequent_itemsets": [format_itemset(item) for item in current_frequents],
            },
            "key_takeaway": takeaway,
        })

        if not current_frequents:
            break

        # Candidate Generation: Join + Prune
        next_level = level + 1
        next_candidates, join_trace = generate_candidates_with_trace(
            current_frequents, next_level, set(current_frequents)
        )

        if not next_candidates and not join_trace.get("joined_pairs"):
            break

        step_num = len(training_steps) + 1
        join_pairs = join_trace.get("joined_pairs", [])
        pruned_subsets = join_trace.get("pruned_by_apriori", [])
        valid_candidates = join_trace.get("valid_candidates", [])

        training_steps.append({
            "step_number": step_num,
            "step_id": f"candidate_gen_C{next_level}",
            "phase": f"Candidate Generation for C{next_level}",
            "title": f"Candidate Generation (L{level} ⨝ L{level} → C{next_level})",
            "concept": "The Apriori Join and Prune Steps",
            "explanation": (
                f"To find frequent {next_level}-itemsets, we do NOT test all possible combinations from scratch. "
                f"Instead, Apriori uses: "
                f"1) JOIN: Combine pairs from L{level} that differ by only 1 item. "
                f"2) PRUNE (The Apriori Property): A candidate {next_level}-itemset is kept ONLY IF "
                f"ALL of its subsets of size {level} are in L{level}. "
                f"If any subset is missing from L{level}, the candidate is discarded immediately without scanning the database!"
            ),
            "formula": {
                "name": "Apriori Pruning Property",
                "expression": r"\forall s \subset c \text{ where } |s| = k-1: s \in L_{k-1}",
                "calculation": f"Every {level}-item subset must exist in L{level}",
            },
            "data": {
                "level": next_level,
                "source_frequent": [format_itemset(item) for item in current_frequents],
                "joined_combinations": join_pairs,
                "pruned_by_apriori": pruned_subsets,
                "final_candidates": [format_itemset(item) for item in valid_candidates],
                "final_candidates_count": len(valid_candidates),
            },
            "key_takeaway": (
                f"By pruning candidates whose subsets are not frequent, we generated only "
                f"{len(valid_candidates)} candidate(s) to check in C{next_level}, avoiding unnecessary database scans!"
            ),
        })

        if not next_candidates:
            break

        current_candidates = next_candidates
        level += 1

    # -------------------------------------------------------------------------
    # RULE GENERATION PHASE
    # -------------------------------------------------------------------------
    rules, rule_steps = generate_rules_with_trace(
        transactions=transactions,
        frequent_itemsets=frequent_itemsets,
        support_map=support_map,
        count_map=count_map,
        min_confidence=min_confidence,
    )

    step_num = len(training_steps) + 1
    training_steps.append({
        "step_number": step_num,
        "step_id": "rule_generation",
        "phase": "Association Rule Mining",
        "title": "Deriving Association Rules (A → B)",
        "concept": "Confidence & Lift Evaluation",
        "explanation": (
            f"From every frequent itemset of size >= 2, we generate association rules of the form A → B. "
            f"A rule means: 'If a shopper buys itemset A, they will also buy itemset B'. "
            f"We calculate Confidence = Support(A ∪ B) / Support(A). "
            f"If Confidence >= {min_confidence:.0%}, the rule is accepted. "
            f"We also calculate Lift: Lift > 1 indicates a positive correlation (buying A increases likelihood of buying B), "
            f"Lift = 1 means independent, and Lift < 1 indicates negative correlation (substitutes)."
        ),
        "formula": {
            "name": "Confidence & Lift",
            "expression": r"\text{Confidence}(A \to B) = \frac{\text{Support}(A \cup B)}{\text{Support}(A)}, \quad \text{Lift} = \frac{\text{Confidence}(A \to B)}{\text{Support}(B)}",
            "calculation": f"Rule accepted if Confidence >= {min_confidence:.0%}",
        },
        "data": {
            "all_evaluated_rules": rule_steps,
            "accepted_rules_count": len(rules),
            "total_rules_tested": len(rule_steps),
        },
        "key_takeaway": (
            f"{len(rules)} strong association rule(s) met the minimum confidence threshold of {min_confidence:.0%}."
        ),
    })

    # -------------------------------------------------------------------------
    # FINAL STEP: Summary & Business Recommendations
    # -------------------------------------------------------------------------
    step_num = len(training_steps) + 1
    training_steps.append({
        "step_number": step_num,
        "step_id": "summary",
        "phase": "Final Summary & Business Action",
        "title": "Mined Results & Real-World Business Strategies",
        "concept": "Applying Market Basket Analysis to Retail Decisions",
        "explanation": (
            f"Apriori successfully mined {len(frequent_itemsets)} frequent itemset(s) and "
            f"{len(rules)} strong association rule(s). "
            f"Retail managers use these rules to design store layouts, bundle complementary products, "
            f"and power e-commerce recommendation systems."
        ),
        "formula": {
            "name": "Summary Metrics",
            "expression": r"\text{Frequent Itemsets} \implies \text{Association Rules} \implies \text{Actionable Strategy}",
            "calculation": f"{len(frequent_itemsets)} itemsets, {len(rules)} rules",
        },
        "data": {
            "frequent_itemsets": [
                {
                    "itemset": format_itemset(item),
                    "size": len(item),
                    "support": f"{supp:.1%}",
                    "count": count,
                }
                for item, supp, count in frequent_itemsets
            ],
            "rules": [
                {
                    "rule": format_rule(r["antecedent"], r["consequent"]),
                    "antecedent": format_itemset(r["antecedent"]),
                    "consequent": format_itemset(r["consequent"]),
                    "support": f"{r['support']:.1%}",
                    "confidence": f"{r['confidence']:.1%}",
                    "lift": f"{r['lift']:.2f}",
                    "interpretation": (
                        "Strong complementary purchase (Lift > 1.2)"
                        if r["lift"] > 1.2
                        else ("Moderate association" if r["lift"] >= 1.0 else "Weak/negative association")
                    ),
                }
                for r in rules
            ],
        },
        "key_takeaway": (
            "Congratulations! You completed the full Apriori workflow from raw baskets to actionable business rules."
        ),
    })

    frequent_itemsets.sort(key=lambda row: (len(row[0]), sorted(row[0])))

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
    frequents: list[Itemset],
    size: int,
    frequent_lookup: set[Itemset],
) -> tuple[list[Itemset], dict[str, Any]]:
    """
    Generate size-k candidates from frequent (size-1)-itemsets,
    recording the Join pairs and Prune decisions.
    """
    joined_pairs: list[dict[str, Any]] = []
    pruned_by_apriori: list[dict[str, Any]] = []
    valid_candidates: set[Itemset] = set()

    sorted_frequents = [tuple(sorted(itemset)) for itemset in frequents]

    # Join step: combine pairs
    for left, right in combinations(sorted_frequents, 2):
        candidate = frozenset(left).union(right)
        if len(candidate) != size:
            continue

        candidate_label = format_itemset(candidate)

        if any(c["candidate"] == candidate_label for c in joined_pairs):
            continue

        # Prune step: check all (size - 1) subsets
        subsets = [frozenset(s) for s in combinations(candidate, size - 1)]
        missing_subsets = [s for s in subsets if s not in frequent_lookup]

        is_valid = len(missing_subsets) == 0

        joined_pairs.append({
            "from_pair": f"{format_itemset(left)} + {format_itemset(right)}",
            "candidate": candidate_label,
            "subsets": [format_itemset(s) for s in subsets],
            "missing_subsets": [format_itemset(s) for s in missing_subsets],
            "passed_prune": is_valid,
            "action": f"ACCEPTED into C{size}" if is_valid else "PRUNED by Apriori property",
        })

        if is_valid:
            valid_candidates.add(candidate)
        else:
            pruned_by_apriori.append({
                "candidate": candidate_label,
                "missing_subset": format_itemset(missing_subsets[0]) if missing_subsets else "",
                "reason": (
                    f"Subset {format_itemset(missing_subsets[0])} is NOT in L{size - 1}. "
                    f"By Apriori downward closure, candidate cannot be frequent!"
                ),
            })

    sorted_valid = sorted(valid_candidates, key=lambda value: tuple(sorted(value)))

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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Generate association rules with detailed breakdown for every candidate rule.
    """
    accepted_rules: list[dict[str, Any]] = []
    rule_evaluations: list[dict[str, Any]] = []

    for itemset, support, itemset_count in frequent_itemsets:
        if len(itemset) < 2:
            continue

        sorted_items = tuple(sorted(itemset))
        for size in range(1, len(sorted_items)):
            for antecedent_items in combinations(sorted_items, size):
                antecedent = frozenset(antecedent_items)
                consequent = itemset.difference(antecedent)

                if antecedent not in support_map or consequent not in support_map:
                    continue

                antecedent_support = support_map[antecedent]
                consequent_support = support_map[consequent]
                antecedent_count = count_map.get(antecedent, 0)

                confidence = support / antecedent_support if antecedent_support > 0 else 0.0
                is_accepted = confidence >= min_confidence

                lift = (
                    confidence / consequent_support
                    if consequent_support > 0
                    else 0.0
                )

                rule_eval = {
                    "rule": format_rule(antecedent, consequent),
                    "antecedent": format_itemset(antecedent),
                    "consequent": format_itemset(consequent),
                    "itemset": format_itemset(itemset),
                    "support": support,
                    "support_pct": f"{support:.1%}",
                    "antecedent_support_pct": f"{antecedent_support:.1%}",
                    "consequent_support_pct": f"{consequent_support:.1%}",
                    "antecedent_count": antecedent_count,
                    "itemset_count": itemset_count,
                    "confidence": confidence,
                    "confidence_pct": f"{confidence:.1%}",
                    "lift": lift,
                    "lift_str": f"{lift:.2f}",
                    "is_accepted": is_accepted,
                    "calculation_formula": (
                        f"Confidence = Support({format_itemset(itemset)}) / Support({format_itemset(antecedent)}) "
                        f"= {support:.1%} / {antecedent_support:.1%} = {confidence:.1%}"
                    ),
                    "lift_formula": (
                        f"Lift = Confidence / Support({format_itemset(consequent)}) "
                        f"= {confidence:.1%} / {consequent_support:.1%} = {lift:.2f}"
                    ),
                    "decision": (
                        f"ACCEPTED ({confidence:.1%} >= {min_confidence:.0%})"
                        if is_accepted
                        else f"REJECTED ({confidence:.1%} < {min_confidence:.0%})"
                    ),
                }

                rule_evaluations.append(rule_eval)

                if is_accepted:
                    accepted_rules.append({
                        "antecedent": antecedent,
                        "consequent": consequent,
                        "support": support,
                        "confidence": confidence,
                        "lift": lift,
                        "rule_eval": rule_eval,
                    })

    accepted_rules.sort(
        key=lambda r: (-r["confidence"], -r["lift"], format_rule(r["antecedent"], r["consequent"]))
    )

    return accepted_rules, rule_evaluations

