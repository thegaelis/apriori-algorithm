"""Verify the active mining engine against exhaustive enumeration."""
import itertools
import random
import unittest

from src.core.apriori import analyze_baskets, build_apriori_trace


def transactions(baskets):
    return [{"tid": f"T{i + 1}", "items": sorted(basket)}
            for i, basket in enumerate(baskets)]


class TraceTests(unittest.TestCase):
    def test_textbook_example(self):
        baskets = [
            {"I1", "I2", "I5"}, {"I2", "I4"}, {"I2", "I3"},
            {"I1", "I2", "I4"}, {"I1", "I3"}, {"I2", "I3"},
            {"I1", "I3"}, {"I1", "I2", "I3", "I5"}, {"I1", "I2", "I3"},
        ]
        result = build_apriori_trace(transactions(baskets), 2, .7)
        self.assertEqual([len(level) for level in result["Lall"] if level], [5, 6, 2])
        self.assertEqual(result["count"]["I1|I2|I5"], 2)
        self.assertIn("I1|I2|I3|I5", result["pruned"])
        self.assertEqual(result["scans"], 3)

    def test_randomized_results_and_rule_metrics(self):
        rng = random.Random(42)
        for case in range(100):
            baskets = [{x for x in "abcde" if rng.random() < .55} for _ in range(8)]
            baskets = [b for b in baskets if b]
            minimum = rng.choice([1, 2, 4, 8])
            confidence = rng.choice([0, .5, .7, 1])
            with self.subTest(case=case):
                result = build_apriori_trace(transactions(baskets), minimum, confidence)
                counts = {}
                for size in range(1, 6):
                    for subset in itertools.combinations("abcde", size):
                        itemset = frozenset(subset)
                        counts[itemset] = sum(itemset <= b for b in baskets)
                expected = {s for s, count in counts.items() if count >= minimum}
                self.assertEqual({frozenset(s) for s in result["freq"]}, expected)
                expected_rules = {}
                for itemset in expected:
                    for size in range(1, len(itemset)):
                        for subset in itertools.combinations(sorted(itemset), size):
                            a = frozenset(subset)
                            b = itemset - a
                            conf = counts[itemset] / counts[a]
                            expected_rules[a, b] = (
                                conf, conf / (counts[b] / len(baskets)), conf >= confidence)
                actual_rules = {(frozenset(r["s"]), frozenset(r["b"])): r
                                for g in result["groups"] for r in g["rules"]}
                self.assertEqual(actual_rules.keys(), expected_rules.keys())
                for key, (conf, lift, accepted) in expected_rules.items():
                    self.assertAlmostEqual(actual_rules[key]["conf"], conf)
                    self.assertAlmostEqual(actual_rules[key]["lift"], lift)
                    self.assertEqual(actual_rules[key]["ok"], accepted)
                self.assertEqual(result["strong"], sum(v[2] for v in expected_rules.values()))

    def test_legacy_adapter_matches_shared_engine(self):
        baskets = [{"a", "b", "c"}, {"a", "b"}, {"a", "c"}, {"b", "c"}]
        trace = build_apriori_trace(transactions(baskets), 2, .5)
        legacy = analyze_baskets(baskets, .5, .5)
        self.assertEqual({itemset for itemset, _, _ in legacy["frequent_itemsets"]},
                         {frozenset(itemset) for itemset in trace["freq"]})
        self.assertEqual(len(legacy["rules"]), trace["strong"])
        for step in legacy["steps"]:
            detailed = next(s for s in legacy["training_steps"]
                            if s["step_id"] == f"scan_filter_L{step['level']}")
            self.assertIs(step["candidates"], detailed["data"]["candidates"])

    def test_empty_no_frequents_and_single_item(self):
        self.assertEqual(analyze_baskets([], .5, .7)["frequent_itemsets"], [])
        self.assertEqual(build_apriori_trace([], 1, .7)["freq"], [])
        self.assertEqual(build_apriori_trace(transactions([{"a"}]), 2, .7)["freq"], [])
        result = build_apriori_trace(transactions([{"a"}, {"a"}]), 1, .7)
        self.assertEqual(result["freq"], [["a"]])
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["steps"][-3]["reason"], "join")

    def test_legacy_zero_support_threshold(self):
        result = analyze_baskets([{"a"}, {"b"}, {"c"}], 0, 0)
        self.assertEqual(len(result["frequent_itemsets"]), 7)
        self.assertEqual(len(result["rules"]), 12)
        self.assertTrue(all(rule["confidence"] == 0 for rule in result["rules"]))


if __name__ == "__main__":
    unittest.main()
