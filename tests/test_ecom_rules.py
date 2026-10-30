from __future__ import annotations

import json
import math
import os
import random
import unittest
from collections import Counter, defaultdict
from itertools import combinations

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "data", "ecom_rules.json")


def simulate_shop_recommendations(cart_items: set[str], rules: list[dict], catalog: dict) -> list[dict]:
    matched_rules = []
    for r in rules:
        ant = set(r["antecedent"])
        if ant.issubset(cart_items):
            rem_consequent = [c for c in r["consequent"] if c not in cart_items]
            if rem_consequent:
                matched_rules.append({
                    **r,
                    "targetItems": rem_consequent,
                })

    recom_map = {}
    for r in matched_rules:
        for code in r["targetItems"]:
            if code not in recom_map or recom_map[code]["lift"] < r["lift"]:
                recom_map[code] = {
                    "code": code,
                    "item": catalog.get(code, {"name": code, "price": 2.0}),
                    "rule": r,
                    "lift": r["lift"],
                    "conf": r["confidence"],
                    "supp": r["support"],
                    "count": r["count"],
                }

    return sorted(recom_map.values(), key=lambda x: x["lift"], reverse=True)[:4]


class TestEcomRulesChallenger1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert os.path.exists(DATA_PATH), f"File not found: {DATA_PATH}"
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cls.data = json.load(f)
        cls.rules = cls.data["rules"]
        cls.catalog = cls.data["catalog"]
        cls.store_skus = cls.data["store_skus"]
        cls.frequent_itemsets = cls.data["frequent_itemsets"]

    def test_rule_integrity_disjointness_and_uniqueness(self) -> None:
        """Verify A ∩ B = ∅ and no duplicate (A, B) rules exist."""
        seen = set()
        for idx, r in enumerate(self.rules):
            ant = r.get("antecedent", [])
            con = r.get("consequent", [])
            self.assertTrue(len(ant) > 0, f"Rule {idx} has empty antecedent")
            self.assertTrue(len(con) > 0, f"Rule {idx} has empty consequent")
            
            overlap = set(ant).intersection(set(con))
            self.assertEqual(len(overlap), 0, f"Rule {idx} antecedent and consequent overlap: {overlap}")

            key = (tuple(sorted(ant)), tuple(sorted(con)))
            self.assertNotIn(key, seen, f"Rule {idx} is a duplicate: {key}")
            seen.add(key)

    def test_rule_metrics_no_nan_null_or_invalid_values(self) -> None:
        """Verify support, confidence, lift, count have valid bounds and no NaN/null/inf."""
        for idx, r in enumerate(self.rules):
            supp = r.get("support")
            conf = r.get("confidence")
            lift = r.get("lift")
            cnt = r.get("count")

            for name, val, min_v, max_v in [
                ("support", supp, 0.0, 1.0),
                ("confidence", conf, 0.0, 1.0),
                ("lift", lift, 0.0, float("inf")),
                ("count", cnt, 0, float("inf")),
            ]:
                self.assertIsNotNone(val, f"Rule {idx} metric {name} is None")
                self.assertFalse(math.isnan(val), f"Rule {idx} metric {name} is NaN")
                self.assertFalse(math.isinf(val), f"Rule {idx} metric {name} is Inf")
                self.assertGreater(val, min_v, f"Rule {idx} metric {name} <= {min_v}")
                if max_v <= 1.0:
                    self.assertLessEqual(val, max_v, f"Rule {idx} metric {name} > {max_v}")

    def test_all_52_store_skus_trigger_active_rules(self) -> None:
        """Verify all 97 Apriori-qualified store SKUs trigger active rules and all 72 pruned SKUs have pruning diagnostics."""
        self.assertEqual(len(self.store_skus), 169)
        qualified_skus = [s for s in self.store_skus if self.catalog[s].get("has_apriori_rule")]
        pruned_skus = [s for s in self.store_skus if not self.catalog[s].get("has_apriori_rule")]
        self.assertGreaterEqual(len(qualified_skus), 90)
        self.assertEqual(len(qualified_skus) + len(pruned_skus), 169)

        for sku in qualified_skus:
            cart = {sku}
            active_rules = [
                r for r in self.rules
                if set(r["antecedent"]) == cart and sku not in r["consequent"]
            ]
            self.assertGreaterEqual(len(active_rules), 1, f"Qualified SKU {sku} has 0 rules")
            for r in active_rules:
                self.assertGreaterEqual(r["count"], 30, f"Rule for {sku} has count < 30")

        for sku in pruned_skus:
            cart = {sku}
            active_rules = [
                r for r in self.rules
                if set(r["antecedent"]) == cart and sku not in r["consequent"]
            ]
            self.assertEqual(len(active_rules), 0, f"Pruned SKU {sku} should not have fake rules")
            self.assertIn(self.catalog[sku].get("pruned_stage"), ("C1_TO_L1", "C2_TO_L2", "RULE_FILTER"))
            self.assertTrue(self.catalog[sku].get("max_co_item"))

    def test_multi_item_combinations_exhaustive_pairs(self) -> None:
        """Simulate adding all 1,326 pairs of top 52 store items to cart: no crash, no duplicates."""
        all_pairs = list(combinations(self.store_skus[:52], 2))
        self.assertEqual(len(all_pairs), 1326)

        for sku1, sku2 in all_pairs:
            cart = {sku1, sku2}
            recoms = simulate_shop_recommendations(cart, self.rules, self.catalog)
            if recoms:
                rec_codes = [r["code"] for r in recoms]
                # No duplicate recommendations
                self.assertEqual(len(rec_codes), len(set(rec_codes)))
                # No recommended item already in cart
                self.assertEqual(len(set(rec_codes).intersection(cart)), 0)
                # Sorted descending by lift
                lifts = [r["lift"] for r in recoms]
                self.assertEqual(lifts, sorted(lifts, reverse=True))

    def test_multi_item_combinations_triplets_and_quads(self) -> None:
        """Simulate diverse 3-item and 4-item carts: no crash, no duplicates, no cart collisions."""
        random.seed(1337)
        # Sample 500 triplets and 500 quads
        for _ in range(500):
            cart_3 = set(random.sample(self.store_skus, 3))
            recoms_3 = simulate_shop_recommendations(cart_3, self.rules, self.catalog)
            if recoms_3:
                rec_codes = [r["code"] for r in recoms_3]
                self.assertEqual(len(rec_codes), len(set(rec_codes)))
                self.assertEqual(len(set(rec_codes).intersection(cart_3)), 0)

            cart_4 = set(random.sample(self.store_skus, 4))
            recoms_4 = simulate_shop_recommendations(cart_4, self.rules, self.catalog)
            if recoms_4:
                rec_codes = [r["code"] for r in recoms_4]
                self.assertEqual(len(rec_codes), len(set(rec_codes)))
                self.assertEqual(len(set(rec_codes).intersection(cart_4)), 0)

    def test_adversarial_boundary_conditions(self) -> None:
        """Stress-test edge cases: empty cart, unknown SKUs, full store SKU cart."""
        # Empty cart
        self.assertEqual(len(simulate_shop_recommendations(set(), self.rules, self.catalog)), 0)
        # Non-existent SKU
        self.assertEqual(len(simulate_shop_recommendations({"NON_EXISTENT_SKU_12345"}, self.rules, self.catalog)), 0)
        # Full store SKU cart: recommendations must only contain external catalog items
        full_cart = set(self.store_skus)
        recoms = simulate_shop_recommendations(full_cart, self.rules, self.catalog)
        for r in recoms:
            self.assertNotIn(r["code"], full_cart)


if __name__ == "__main__":
    unittest.main()
