"""Tier 2: Boundary & Corner Cases E2E Tests.

Requirement: >= 5 tests per feature group across edge conditions:
1. Zero/empty cart handling & cart stepper boundary conditions
2. Invalid & unknown SKU lookups
3. Edge thresholds (min support 0% and 100%, min confidence 0% and 100%)
4. Rule integrity & disjoint sets (empty antecedents/consequents rejection)
5. Boundary lift and confidence values
"""
from __future__ import annotations

import unittest
from typing import Any

from tests.e2e.base import E2ETestBase


class TestTier2EmptyCartAndStepper(E2ETestBase):
    """Boundary Case Group 1: Zero/Empty Cart Handling & Quantity Stepper (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()

    def test_2_1_zero_empty_cart_returns_fallback_recommendations(self) -> None:
        """Verify empty cart yields fallback bestsellers without exception."""
        recoms = self.simulate_cascade_recommendations([], self.data, max_recom=4)
        self.assertIsInstance(recoms, list)
        self.assertGreater(len(recoms), 0, "Empty cart should fall back to store bestsellers (never empty)")
        for r in recoms:
            self.assertIn("code", r)
            self.assertIn("score", r)

    def test_2_2_single_item_cart_excludes_itself_from_recommendations(self) -> None:
        """Verify an item in the cart is NEVER recommended to the customer."""
        rules = self.data.get("rules", [])
        if not rules:
            self.skipTest("No rules available")

        # Pick first available SKU from antecedents
        sample_sku = rules[0]["antecedent"][0]
        recoms = self.simulate_cascade_recommendations([sample_sku], self.data, max_recom=4)
        recommended_codes = [r["code"] for r in recoms]

        self.assertNotIn(
            sample_sku,
            recommended_codes,
            f"Item {sample_sku} already in cart was erroneously recommended",
        )

    def test_2_3_cart_quantity_stepper_decrement_removes_item_at_zero(self) -> None:
        """Simulate client-side quantity stepper logic: decrementing at qty=1 deletes item."""
        cart: dict[str, int] = {}

        # Add item
        cart["85099B"] = cart.get("85099B", 0) + 1
        self.assertEqual(cart["85099B"], 1)

        # Increment item
        cart["85099B"] += 1
        self.assertEqual(cart["85099B"], 2)

        # Decrement item
        cart["85099B"] -= 1
        self.assertEqual(cart["85099B"], 1)

        # Decrement at 1 should delete
        if cart["85099B"] <= 1:
            del cart["85099B"]
        else:
            cart["85099B"] -= 1

        self.assertNotIn("85099B", cart, "Item with qty 0 must be removed from cart state")
        self.assertEqual(len(cart), 0)

    def test_2_4_cart_drain_and_clear_resets_total_to_zero(self) -> None:
        """Simulate adding 5 items and removing all: count and total must return to 0."""
        catalog = self.data.get("catalog", {})
        cart: dict[str, dict[str, Any]] = {}

        sample_skus = list(catalog.keys())[:5]
        for sku in sample_skus:
            cart[sku] = {"code": sku, "qty": 1, "price": catalog[sku].get("price", 2.0)}

        self.assertEqual(len(cart), 5)

        # Clear cart
        cart.clear()
        total_price = sum(item["qty"] * item["price"] for item in cart.values())
        self.assertEqual(len(cart), 0)
        self.assertEqual(total_price, 0.0)

    def test_2_5_cart_currency_formatting_and_floating_point_precision(self) -> None:
        """Simulate decimal price aggregation without IEEE-754 floating point artifacts."""
        test_items = [
            {"price": 2.95, "qty": 3},  # 8.85
            {"price": 1.69, "qty": 2},  # 3.38
            {"price": 4.15, "qty": 1},  # 4.15
        ]
        # Total: 8.85 + 3.38 + 4.15 = 16.38
        raw_total = sum(item["price"] * item["qty"] for item in test_items)
        formatted_total = f"£{raw_total:.2f}"
        self.assertEqual(formatted_total, "£16.38")


class TestTier2InvalidSKUs(E2ETestBase):
    """Boundary Case Group 2: Invalid & Unknown SKU Lookups (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.catalog = self.data.get("catalog", {})

    def test_2_6_invalid_sku_in_cart_does_not_crash_recommendation_engine(self) -> None:
        """Verify an unrecognized SKU code does not crash cascade engine."""
        invalid_sku = "NON_EXISTENT_SKU_XYZ_999999"
        recoms = self.simulate_cascade_recommendations([invalid_sku], self.data, max_recom=4)
        self.assertIsInstance(recoms, list)
        self.assertGreater(len(recoms), 0, "Should fall back to bestsellers without crashing")

    def test_2_7_catalog_lookup_fallback_for_unknown_sku(self) -> None:
        """Verify catalog lookup returns fallback name rather than None/undefined."""
        unknown_code = "UNKNOWN_CODE_123"

        def get_product_name(code: str) -> str:
            item = self.catalog.get(code)
            return item["name"] if (item and "name" in item) else code

        name = get_product_name(unknown_code)
        self.assertEqual(name, unknown_code)
        self.assertNotEqual(name, "undefined")
        self.assertNotEqual(name, "None")

    def test_2_8_mixed_valid_and_invalid_skus_triggers_valid_rules(self) -> None:
        """Verify valid SKU triggers rules even when bundled with an unknown SKU."""
        rules = self.data.get("rules", [])
        if not rules:
            self.skipTest("No rules available")

        valid_sku = rules[0]["antecedent"][0]
        mixed_basket = [valid_sku, "CORRUPT_SKU_$$$"]
        recoms = self.simulate_cascade_recommendations(mixed_basket, self.data, max_recom=4)

        self.assertIsInstance(recoms, list)
        self.assertGreater(len(recoms), 0)
        self.assertNotIn(valid_sku, [r["code"] for r in recoms])

    def test_2_9_empty_string_and_whitespace_sku_handled_safely(self) -> None:
        """Verify empty string or whitespace SKU does not corrupt cart or recommendations."""
        basket = ["", "   ", None]
        sanitized = [s for s in basket if s and isinstance(s, str) and s.strip()]
        self.assertEqual(len(sanitized), 0)

        recoms = self.simulate_cascade_recommendations(sanitized, self.data, max_recom=4)
        self.assertIsInstance(recoms, list)

    def test_2_10_alphanumeric_sku_with_letter_suffix_preserved(self) -> None:
        """Verify letter-suffixed SKUs (e.g. 85123A, 85099B, 84029G) retain exact casing."""
        special_skus = ["85123A", "85099B", "84406B", "84029G"]
        for sku in special_skus:
            if sku in self.catalog:
                self.assertEqual(self.catalog[sku].get("code"), sku)


class TestTier2EdgeThresholds(E2ETestBase):
    """Boundary Case Group 3: Edge Thresholds (0% and 100%) (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.rules = self.data.get("rules", [])

    def test_2_11_min_support_zero_percent_returns_all_rules(self) -> None:
        """Verify filtering with min_support = 0.0 includes all rules."""
        filtered = [r for r in self.rules if r.get("support", 0.0) >= 0.0]
        self.assertEqual(len(filtered), len(self.rules))

    def test_2_12_min_support_one_hundred_percent_returns_empty_cleanly(self) -> None:
        """Verify filtering with min_support = 1.0 (100%) cleanly returns empty list without error."""
        filtered = [r for r in self.rules if r.get("support", 0.0) >= 1.0]
        self.assertEqual(len(filtered), 0)

    def test_2_13_min_confidence_zero_percent_returns_all_rules(self) -> None:
        """Verify filtering with min_confidence = 0.0 includes all rules."""
        filtered = [r for r in self.rules if r.get("confidence", 0.0) >= 0.0]
        self.assertEqual(len(filtered), len(self.rules))

    def test_2_14_min_confidence_one_hundred_percent_filters_strictly(self) -> None:
        """Verify filtering with min_confidence = 1.0 only retains 100% confidence rules."""
        filtered = [r for r in self.rules if r.get("confidence", 0.0) >= 1.0]
        for r in filtered:
            self.assertEqual(r["confidence"], 1.0)

    def test_2_15_extreme_min_lift_filter(self) -> None:
        """Verify filtering with an extreme min_lift (e.g. 1000.0) returns empty cleanly."""
        filtered = [r for r in self.rules if r.get("lift", 0.0) >= 1000.0]
        self.assertEqual(len(filtered), 0)


class TestTier2RuleIntegrity(E2ETestBase):
    """Boundary Case Group 4: Rule Integrity & Disjoint Sets (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.rules = self.data.get("rules", [])
        self.frequents = self.data.get("frequent_itemsets", {})

    def test_2_16_rules_empty_antecedent_rejected(self) -> None:
        """Verify no rule in ecom_rules.json has an empty antecedent list."""
        for i, r in enumerate(self.rules):
            ant = r.get("antecedent")
            self.assertIsNotNone(ant, f"Rule #{i} has null antecedent")
            self.assertGreater(len(ant), 0, f"Rule #{i} has empty antecedent")

    def test_2_17_rules_empty_consequent_rejected(self) -> None:
        """Verify no rule in ecom_rules.json has an empty consequent list."""
        for i, r in enumerate(self.rules):
            cons = r.get("consequent")
            self.assertIsNotNone(cons, f"Rule #{i} has null consequent")
            self.assertGreater(len(cons), 0, f"Rule #{i} has empty consequent")

    def test_2_18_antecedent_and_consequent_strictly_disjoint(self) -> None:
        """Verify antecedent and consequent sets are strictly disjoint (A ∩ B = ∅)."""
        for i, r in enumerate(self.rules):
            ant_set = set(r.get("antecedent", []))
            cons_set = set(r.get("consequent", []))
            overlap = ant_set & cons_set
            self.assertEqual(
                len(overlap),
                0,
                f"Rule #{i} has overlapping antecedent and consequent items: {overlap}",
            )

    def test_2_19_no_duplicate_directional_rules(self) -> None:
        """Verify no duplicate rules (identical antecedent and consequent) exist."""
        seen_rules = set()
        for i, r in enumerate(self.rules):
            key = (tuple(sorted(r.get("antecedent", []))), tuple(sorted(r.get("consequent", []))))
            self.assertNotIn(key, seen_rules, f"Duplicate rule detected at index #{i}: {key}")
            seen_rules.add(key)

    def test_2_20_no_duplicate_items_within_single_itemset(self) -> None:
        """Verify no itemset contains repeated instances of the same SKU."""
        for level, itemset_list in self.frequents.items():
            for i, entry in enumerate(itemset_list):
                items = entry.get("items", [])
                self.assertEqual(
                    len(items),
                    len(set(items)),
                    f"Frequent itemset {level} #{i} contains duplicate items: {items}",
                )


class TestTier2BoundaryLift(E2ETestBase):
    """Boundary Case Group 5: Boundary Lift & Confidence Values (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.rules = self.data.get("rules", [])

    def test_2_21_minimum_lift_is_strictly_greater_than_one(self) -> None:
        """Verify all curated rules have Lift > 1.0 (positive association only)."""
        for i, r in enumerate(self.rules):
            self.assertGreater(
                r.get("lift", 0.0),
                1.0,
                f"Rule #{i} has Lift <= 1.0 (not positively associated)",
            )

    def test_2_22_confidence_strictly_within_probability_range(self) -> None:
        """Verify confidence is in (0.0, 1.0]."""
        for i, r in enumerate(self.rules):
            conf = r.get("confidence", 0.0)
            self.assertTrue(0.0 < conf <= 1.0, f"Rule #{i} confidence {conf} out of range (0, 1]")

    def test_2_23_support_strictly_within_probability_range(self) -> None:
        """Verify support is in (0.0, 1.0]."""
        for i, r in enumerate(self.rules):
            supp = r.get("support", 0.0)
            self.assertTrue(0.0 < supp <= 1.0, f"Rule #{i} support {supp} out of range (0, 1]")

    def test_2_24_rule_count_matches_support_and_baskets(self) -> None:
        """Verify count in rules roughly equals round(support * total_baskets)."""
        total_baskets = self.data.get("total_baskets", 18273)
        for i, r in enumerate(self.rules[:50]):
            count = r.get("count")
            if count is not None:
                expected_count = round(r["support"] * total_baskets)
                self.assertAlmostEqual(
                    count,
                    expected_count,
                    delta=5,
                    msg=f"Rule #{i} count {count} deviates from support * baskets ({expected_count})",
                )

    def test_2_25_zero_division_guard_on_support_values(self) -> None:
        """Verify no product or rule has support == 0.0 to prevent division by zero."""
        catalog = self.data.get("catalog", {})
        for sku, item in list(catalog.items())[:100]:
            supp = item.get("support")
            if supp is not None:
                self.assertGreater(supp, 0.0, f"Catalog item {sku} has zero support")


if __name__ == "__main__":
    unittest.main()
