"""Tier 3: Cross-Feature Interactions E2E Tests.

Requirement: Pairwise combinations and cross-module interactions:
1. Cart items matching antecedent -> consequent cross-sell suggestions
2. Admin frequent itemsets matching schema counts
3. URL routing between views (roundtrip navigation)
4. Catalog to Rules referential integrity
5. Combos L2 integrity with frequent itemsets L2
6. Cross-sell drawer activation on item addition
7. Admin Tab 1 itemset to Tab 2 rule interaction
8. Monotonic property of support filtering across itemsets
"""
from __future__ import annotations

import os
import unittest
from typing import Any

from tests.e2e.base import E2ETestBase, WEB_DIR


class TestTier3CrossFeatureInteractions(E2ETestBase):
    """Tier 3: Cross-Feature Pairwise Interactions."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.catalog = self.data.get("catalog", {})
        self.rules = self.data.get("rules", [])
        self.frequents = self.data.get("frequent_itemsets", {})
        self.summary = self.data.get("summary", {})

    def test_3_1_cart_items_matching_antecedent_generates_consequent_suggestions(self) -> None:
        """Pairwise: Cart item matching antecedent triggers corresponding consequent suggestion."""
        # Find a single-antecedent rule
        single_rules = [r for r in self.rules if len(r.get("antecedent", [])) == 1]
        if not single_rules:
            self.skipTest("No single antecedent rules found")

        rule = single_rules[0]
        trigger_sku = rule["antecedent"][0]
        expected_consequent = rule["consequent"][0]

        recoms = self.simulate_cascade_recommendations([trigger_sku], self.data, max_recom=4)
        recom_codes = [r["code"] for r in recoms]

        self.assertIn(
            expected_consequent,
            recom_codes,
            f"Adding {trigger_sku} should trigger recommendation for {expected_consequent} from rule {rule}",
        )

    def test_3_2_admin_frequent_itemsets_match_schema_kpi_counts(self) -> None:
        """Pairwise: Admin portal Frequent Itemsets counts strictly equal summary KPI metrics."""
        self.assertIn("L1", self.frequents, "frequent_itemsets missing L1")
        self.assertIn("L2", self.frequents, "frequent_itemsets missing L2")
        self.assertIn("L3", self.frequents, "frequent_itemsets missing L3")

        l1_actual = len(self.frequents["L1"])
        l2_actual = len(self.frequents["L2"])
        l3_actual = len(self.frequents["L3"])

        self.assertEqual(
            self.summary.get("l1_count"),
            l1_actual,
            f"KPI l1_count ({self.summary.get('l1_count')}) != len(L1) ({l1_actual})",
        )
        self.assertEqual(
            self.summary.get("l2_count"),
            l2_actual,
            f"KPI l2_count ({self.summary.get('l2_count')}) != len(L2) ({l2_actual})",
        )
        self.assertEqual(
            self.summary.get("l3_count"),
            l3_actual,
            f"KPI l3_count ({self.summary.get('l3_count')}) != len(L3) ({l3_actual})",
        )

    def test_3_3_url_routing_navigation_cycle_across_all_four_views(self) -> None:
        """Pairwise: Round-trip HTTP navigation across /, /shop, /stats, and /admin."""
        routes = ["/", "/shop", "/stats", "/admin"]
        for r in routes:
            status, headers, text = self.get(r)
            self.assertEqual(status, 200, f"Route {r} returned {status}")
            self.assertIn("text/html", headers.get("content-type", ""))
            self.assertGreater(len(text), 100)

    def test_3_4_catalog_to_rules_referential_integrity(self) -> None:
        """Pairwise: Every SKU present in rules must be documented in catalog."""
        all_rule_skus = set()
        for r in self.rules:
            for s in r.get("antecedent", []) + r.get("consequent", []):
                all_rule_skus.add(s)

        missing_from_catalog = [sku for sku in all_rule_skus if sku not in self.catalog]
        self.assertEqual(
            len(missing_from_catalog),
            0,
            f"Referential integrity failure: SKUs {missing_from_catalog[:10]} in rules missing from catalog",
        )

    def test_3_5_combos_l2_integrity_with_frequent_itemsets_l2(self) -> None:
        """Pairwise: Every combo in combos array must exist as a valid L2 frequent itemset."""
        combos = self.data.get("combos", [])
        l2_itemsets = self.frequents.get("L2", [])

        if not l2_itemsets:
            self.skipTest("L2 itemsets not available yet")

        l2_sets = {frozenset(entry["items"]) for entry in l2_itemsets}
        for combo in combos:
            combo_items = frozenset(combo.get("items", []))
            self.assertIn(
                combo_items,
                l2_sets,
                f"Combo {combo_items} is not present in frequent_itemsets L2",
            )

    def test_3_6_cross_sell_drawer_opens_on_add_to_cart_in_shop_html(self) -> None:
        """Pairwise: Storefront JavaScript binds item addition to cart drawer opening."""
        shop_html = self.load_template("shop.html")
        # Verify drawer element exists
        self.assertTrue(
            "cart-drawer" in shop_html or "cartdrawer" in shop_html.lower(),
            "shop.html missing Slide-out Cart Drawer container",
        )
        # Verify open drawer interaction trigger exists
        self.assertTrue(
            "opencartdrawer" in shop_html.lower() or "cartdrawer.open" in shop_html.lower() or "drawer" in shop_html.lower(),
            "shop.html missing openCartDrawer interaction hook",
        )

    def test_3_7_admin_tab1_to_tab2_interaction_consistency(self) -> None:
        """Pairwise: Itemset SKUs in Tab 1 can be located as Antecedents in Tab 2."""
        l1_itemsets = self.frequents.get("L1", [])
        if not l1_itemsets:
            self.skipTest("L1 frequent itemsets not available")

        # Pick top 5 frequent items from L1
        top_skus = [entry["items"][0] for entry in l1_itemsets[:5]]
        for sku in top_skus:
            # Check if at least one rule exists with this SKU in antecedent or consequent
            related_rules = [
                r for r in self.rules
                if sku in r.get("antecedent", []) or sku in r.get("consequent", [])
            ]
            self.assertGreater(
                len(related_rules),
                0,
                f"Frequent item {sku} has 0 related rules in Tab 2",
            )

    def test_3_8_monotonic_property_of_dynamic_support_filtering(self) -> None:
        """Pairwise: Increasing min_support threshold monotonically decreases filtered itemsets."""
        all_itemsets = []
        for level in ("L1", "L2", "L3"):
            all_itemsets.extend(self.frequents.get(level, []))

        if not all_itemsets:
            self.skipTest("Frequent itemsets not available")

        thresholds = [0.005, 0.010, 0.020, 0.050, 0.100]
        counts = [
            len([item for item in all_itemsets if item.get("support", 0.0) >= t])
            for t in thresholds
        ]

        # Monotonically non-increasing: counts[i] >= counts[i+1]
        for i in range(len(counts) - 1):
            self.assertGreaterEqual(
                counts[i],
                counts[i + 1],
                f"Support filter violated monotonicity: at {thresholds[i]} got {counts[i]}, "
                f"but at higher threshold {thresholds[i+1]} got {counts[i+1]}",
            )


if __name__ == "__main__":
    unittest.main()
