from __future__ import annotations

import unittest

from src.core.apriori import analyze_baskets, parse_baskets


class AprioriDemoTests(unittest.TestCase):
    def test_parse_baskets(self) -> None:
        baskets = parse_baskets("milk, bread\n\n bread ; butter ")
        self.assertEqual(len(baskets), 2)
        self.assertIn("milk", baskets[0])
        self.assertIn("bread", baskets[1])

    def test_apriori_finds_expected_itemsets(self) -> None:
        baskets = parse_baskets(
            """milk, bread, butter
bread, diaper, beer, eggs
milk, diaper, bread, cola
bread, milk, diaper, beer
milk, bread, diaper, cola"""
        )
        result = analyze_baskets(baskets, min_support=0.6, min_confidence=0.75)

        itemsets = {tuple(sorted(itemset)): round(support, 2) for itemset, support, _ in result["frequent_itemsets"]}
        self.assertEqual(itemsets[("bread",)], 1.0)
        self.assertEqual(itemsets[("milk",)], 0.8)
        self.assertEqual(itemsets[("diaper",)], 0.8)
        self.assertEqual(itemsets[("bread", "milk")], 0.8)
        self.assertEqual(itemsets[("bread", "diaper")], 0.8)
        self.assertGreaterEqual(len(result["rules"]), 1)
        self.assertGreaterEqual(len(result["steps"]), 1)
        self.assertGreaterEqual(len(result["training_steps"]), 4)

    def test_pedagogical_training_steps(self) -> None:
        baskets = parse_baskets(
            """milk, bread, butter
bread, diaper, beer
milk, diaper, bread"""
        )
        result = analyze_baskets(baskets, min_support=0.5, min_confidence=0.6)
        step_ids = [s["step_id"] for s in result["training_steps"]]
        self.assertIn("setup", step_ids)
        self.assertIn("scan_filter_L1", step_ids)
        self.assertIn("rule_generation", step_ids)
        self.assertIn("summary", step_ids)

        # Check setup step has formula and calculation details
        setup_step = result["training_steps"][0]
        self.assertEqual(setup_step["step_id"], "setup")
        self.assertIn("formula", setup_step)
        self.assertIn("data", setup_step)


if __name__ == "__main__":
    unittest.main()
