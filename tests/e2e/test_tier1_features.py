"""Tier 1: Feature Coverage E2E Tests.

Requirement: >= 5 tests per feature across all primary capabilities from ORIGINAL_REQUEST.md:
1. Retail rule mining & data schema (rules non-empty, frequent itemsets L1/L2/L3, summary metrics)
2. Store product coverage (categories & store SKUs active rules)
3. Backend HTTP routes (GET /, /shop, /stats, /admin, /api/ecom-rules, /api/retail-stats)
4. Admin portal structure & metrics (KPI cards, Tab 1, Tab 2, Tab 3, Clean Light SaaS)
5. Global navigation bar consistency across all 4 HTML templates
"""
from __future__ import annotations

import json
import os
import re
import unittest
from typing import Any

from tests.e2e.base import E2ETestBase, PROJECT_ROOT, WEB_DIR, DATA_DIR


class TestTier1Feature1DataSchema(E2ETestBase):
    """Feature 1: Retail Rule Mining & Data Schema Coverage (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()

    def test_1_1_rules_array_non_empty_and_valid_types(self) -> None:
        """Verify rules array is non-empty and each rule has valid typed fields."""
        rules = self.data.get("rules")
        self.assertIsInstance(rules, list, "ecom_rules.json must contain a 'rules' list")
        self.assertGreater(len(rules), 0, "Rules list must not be empty")

        for i, r in enumerate(rules[:50]):  # check sample for speed and thoroughness
            self.assertIn("antecedent", r, f"Rule #{i} missing 'antecedent'")
            self.assertIn("consequent", r, f"Rule #{i} missing 'consequent'")
            self.assertIsInstance(r["antecedent"], list, f"Rule #{i} antecedent must be list")
            self.assertIsInstance(r["consequent"], list, f"Rule #{i} consequent must be list")
            self.assertGreater(len(r["antecedent"]), 0, f"Rule #{i} antecedent is empty")
            self.assertGreater(len(r["consequent"]), 0, f"Rule #{i} consequent is empty")
            self.assertIsInstance(r.get("support"), (int, float), f"Rule #{i} support invalid")
            self.assertIsInstance(r.get("confidence"), (int, float), f"Rule #{i} confidence invalid")
            self.assertIsInstance(r.get("lift"), (int, float), f"Rule #{i} lift invalid")

    def test_1_2_frequent_itemsets_l1_l2_l3_presence_and_structure(self) -> None:
        """Verify frequent_itemsets key exists with L1, L2, and L3 tiers."""
        self.assertIn(
            "frequent_itemsets",
            self.data,
            "ecom_rules.json must contain 'frequent_itemsets' dictionary for Admin portal",
        )
        frequents = self.data["frequent_itemsets"]
        self.assertIsInstance(frequents, dict, "'frequent_itemsets' must be an object with L1, L2, L3")
        self.assertIn("L1", frequents, "'frequent_itemsets' must contain 'L1'")
        self.assertIn("L2", frequents, "'frequent_itemsets' must contain 'L2'")
        self.assertIn("L3", frequents, "'frequent_itemsets' must contain 'L3'")

        self.assertGreater(len(frequents["L1"]), 0, "L1 frequent itemsets must not be empty")
        self.assertGreater(len(frequents["L2"]), 0, "L2 frequent itemsets must not be empty")
        self.assertGreater(len(frequents["L3"]), 0, "L3 frequent itemsets must not be empty")

        # Validate item sizes per tier
        for itemset in frequents["L1"][:20]:
            self.assertEqual(len(itemset["items"]), 1, "L1 itemsets must contain exactly 1 item")
            self.assertGreater(itemset["support"], 0.0)
        for itemset in frequents["L2"][:20]:
            self.assertEqual(len(itemset["items"]), 2, "L2 itemsets must contain exactly 2 items")
            self.assertGreater(itemset["support"], 0.0)
        for itemset in frequents["L3"][:20]:
            self.assertEqual(len(itemset["items"]), 3, "L3 itemsets must contain exactly 3 items")
            self.assertGreater(itemset["support"], 0.0)

    def test_1_3_summary_metrics_structure_and_types(self) -> None:
        """Verify 'summary' metrics dictionary exists with all required KPI fields."""
        self.assertIn(
            "summary",
            self.data,
            "ecom_rules.json must contain 'summary' object for Executive KPIs",
        )
        summary = self.data["summary"]
        required_fields = [
            "total_baskets",
            "total_catalog_products",
            "store_products_count",
            "l1_count",
            "l2_count",
            "l3_count",
            "total_frequent_itemsets",
            "curated_rules_count",
            "max_lift",
            "min_confidence",
            "min_support",
            "store_coverage_pct",
        ]
        for field in required_fields:
            self.assertIn(field, summary, f"Summary object missing required KPI field: {field}")

    def test_1_4_summary_counts_strictly_match_itemset_and_rule_lengths(self) -> None:
        """Verify summary counts match actual array lengths in the JSON."""
        summary = self.data.get("summary", {})
        frequents = self.data.get("frequent_itemsets", {})
        rules = self.data.get("rules", [])

        if frequents:
            self.assertEqual(
                summary.get("l1_count"),
                len(frequents.get("L1", [])),
                "summary.l1_count must match len(frequent_itemsets.L1)",
            )
            self.assertEqual(
                summary.get("l2_count"),
                len(frequents.get("L2", [])),
                "summary.l2_count must match len(frequent_itemsets.L2)",
            )
            self.assertEqual(
                summary.get("l3_count"),
                len(frequents.get("L3", [])),
                "summary.l3_count must match len(frequent_itemsets.L3)",
            )
            expected_total_freq = (
                len(frequents.get("L1", []))
                + len(frequents.get("L2", []))
                + len(frequents.get("L3", []))
            )
            self.assertEqual(
                summary.get("total_frequent_itemsets"),
                expected_total_freq,
                "summary.total_frequent_itemsets must equal L1 + L2 + L3 counts",
            )

        self.assertEqual(
            summary.get("curated_rules_count"),
            len(rules),
            "summary.curated_rules_count must match len(rules)",
        )

    def test_1_5_rule_statistical_consistency_and_lift_bounds(self) -> None:
        """Verify rules have positive support, confidence in (0, 1], and lift > 1.0."""
        rules = self.data.get("rules", [])
        for i, r in enumerate(rules):
            supp = r.get("support", 0.0)
            conf = r.get("confidence", 0.0)
            lift = r.get("lift", 0.0)

            self.assertGreater(supp, 0.0, f"Rule #{i} has non-positive support: {supp}")
            self.assertLessEqual(supp, 1.0, f"Rule #{i} has support > 1.0: {supp}")
            self.assertGreater(conf, 0.0, f"Rule #{i} has non-positive confidence: {conf}")
            self.assertLessEqual(conf, 1.0, f"Rule #{i} has confidence > 1.0: {conf}")
            self.assertGreater(lift, 1.0, f"Rule #{i} has lift <= 1.0 (not a positive correlation): {lift}")


class TestTier1Feature2ProductCoverage(E2ETestBase):
    """Feature 2: Store Product Coverage & Category Diversity (>= 5 tests)."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.catalog = self.data.get("catalog", {})
        self.rules = self.data.get("rules", [])

    def test_2_1_curated_store_skus_defined(self) -> None:
        """Verify store_skus list is defined with >= 48 curated products."""
        store_skus = self.data.get("store_skus")
        self.assertIsNotNone(store_skus, "ecom_rules.json must contain 'store_skus' list")
        self.assertIsInstance(store_skus, list, "'store_skus' must be a list of SKU codes")
        self.assertGreaterEqual(
            len(store_skus),
            48,
            f"Curated store products count {len(store_skus)} is less than required 48 SKUs",
        )

    def test_2_2_all_curated_store_skus_have_active_single_item_rules(self) -> None:
        """Verify all Apriori-qualified store products have >= 1 active rule and pruned items have pruning metadata."""
        store_skus = self.data.get("store_skus", [])
        qualified_skus = [s for s in store_skus if self.catalog.get(s, {}).get("has_apriori_rule")]
        pruned_skus = [s for s in store_skus if not self.catalog.get(s, {}).get("has_apriori_rule")]

        single_ant_skus = set()
        for r in self.rules:
            ant = r.get("antecedent", [])
            if len(ant) == 1:
                single_ant_skus.add(ant[0])

        uncovered_qualified = [sku for sku in qualified_skus if sku not in single_ant_skus]
        self.assertEqual(
            len(uncovered_qualified),
            0,
            f"Qualified store SKUs missing single-item rules: {uncovered_qualified}",
        )
        for sku in pruned_skus:
            self.assertNotIn(sku, single_ant_skus, f"Pruned SKU {sku} should not have fake single-item rules")
            self.assertIn(
                self.catalog[sku].get("pruned_stage"),
                ("C1_TO_L1", "C2_TO_L2", "RULE_FILTER"),
            )

    def test_2_3_all_seven_product_categories_present_in_rules(self) -> None:
        """Verify rules cover all 7 required merchandise categories."""
        required_categories = {"DAIRY", "PRODUCE", "BAKERY", "MEAT", "DRINKS", "SNACKS", "PANTRY"}
        rule_categories = set()

        for r in self.rules:
            for sku in r.get("antecedent", []) + r.get("consequent", []):
                cat = self.catalog.get(sku, {}).get("category")
                if cat:
                    rule_categories.add(cat)

        missing_categories = required_categories - rule_categories
        self.assertEqual(
            len(missing_categories),
            0,
            f"Rules fail to cover required product categories: {missing_categories}. "
            f"Found categories: {rule_categories}",
        )

    def test_2_4_rule_diversity_eliminates_herb_marker_choking_bug(self) -> None:
        """Verify distinct SKUs in rule antecedents is >= 25 (choking bug had only 8 SKUs)."""
        distinct_ant_skus = {sku for r in self.rules for sku in r.get("antecedent", [])}
        self.assertGreaterEqual(
            len(distinct_ant_skus),
            25,
            f"Distinct SKUs across rule antecedents is only {len(distinct_ant_skus)}, "
            f"indicating herb-marker choking bug is still active! Expected >= 25 SKUs.",
        )

    def test_2_5_catalog_contains_rich_metadata_for_all_curated_skus(self) -> None:
        """Verify every store product in catalog has name, price, category, and icon."""
        store_skus = self.data.get("store_skus", list(self.catalog.keys())[:52])
        for sku in store_skus:
            self.assertIn(sku, self.catalog, f"Store SKU {sku} not found in catalog")
            item = self.catalog[sku]
            self.assertTrue(item.get("name"), f"SKU {sku} has empty name")
            self.assertIsInstance(item.get("price"), (int, float), f"SKU {sku} has invalid price")
            self.assertGreater(item.get("price", 0), 0, f"SKU {sku} price must be > 0")
            self.assertTrue(item.get("category"), f"SKU {sku} missing category field")
            self.assertTrue(item.get("icon"), f"SKU {sku} missing icon field")


class TestTier1Feature3HTTPRoutes(E2ETestBase):
    """Feature 3: Backend HTTP Routes Coverage (>= 5 tests)."""

    def test_3_1_route_root_index_html(self) -> None:
        """Verify GET / and /index.html return 200 OK with text/html."""
        for path in ("/", "/index.html"):
            status, headers, text = self.get(path)
            self.assertEqual(status, 200, f"GET {path} failed with status {status}")
            self.assertIn("text/html", headers.get("content-type", ""))
            self.assertIn("<html", text.lower())

    def test_3_2_route_shop_html(self) -> None:
        """Verify GET /shop and /shop.html return 200 OK with text/html."""
        for path in ("/shop", "/shop.html"):
            status, headers, text = self.get(path)
            self.assertEqual(status, 200, f"GET {path} failed with status {status}")
            self.assertIn("text/html", headers.get("content-type", ""))
            self.assertIn("<html", text.lower())

    def test_3_3_route_dataset_html(self) -> None:
        """Verify GET /dataset and /dataset.html return 200 OK with text/html."""
        for path in ("/dataset", "/dataset.html"):
            status, headers, text = self.get(path)
            self.assertEqual(status, 200, f"GET {path} failed with status {status}")
            self.assertIn("text/html", headers.get("content-type", ""))
            self.assertIn("<html", text.lower())

    def test_3_4_legacy_routes_redirect_to_dataset(self) -> None:
        """Verify legacy /stats and /admin routes redirect 301 to /dataset."""
        for path in ("/stats", "/stats.html", "/admin", "/admin.html"):
            status, headers, text = self.get(path)
            self.assertEqual(
                status,
                301,
                f"GET {path} should return 301 redirect to /dataset but got {status}",
            )
            self.assertEqual(headers.get("location"), "/dataset")

    def test_3_5_api_routes_return_valid_json_with_correct_content_type(self) -> None:
        """Verify GET /api/ecom-rules and /api/dataset-stats (or /api/retail-stats) return 200 OK application/json."""
        # /api/ecom-rules
        status, headers, data = self.get_json("/api/ecom-rules")
        self.assertEqual(status, 200, f"GET /api/ecom-rules failed with status {status}")
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertIsInstance(data, dict, "Expected JSON object from /api/ecom-rules")
        self.assertIn("rules", data)

        # /api/dataset-stats (and legacy alias /api/retail-stats)
        for stat_path in ("/api/dataset-stats", "/api/retail-stats"):
            status, headers, stats = self.get_json(stat_path)
            self.assertEqual(status, 200, f"GET {stat_path} failed with status {status}")
            self.assertIn("application/json", headers.get("content-type", ""))
            self.assertIsInstance(stats, dict, f"Expected JSON object from {stat_path}")

    def test_3_6_non_existent_endpoint_returns_404(self) -> None:
        """Verify unknown paths return 404 Not Found."""
        status, _, _ = self.get("/api/unknown-endpoint-xyz-987")
        self.assertEqual(status, 404)


class TestTier1Feature4AdminPortal(E2ETestBase):
    """Feature 4: Unified Dataset Visualizer Structure (>= 5 tests)."""

    def setUp(self) -> None:
        dataset_path = os.path.join(WEB_DIR, "dataset.html")
        self.dataset_exists = os.path.exists(dataset_path)
        self.dataset_html = self.load_template("dataset.html") if self.dataset_exists else ""

    def test_4_1_dataset_template_file_exists(self) -> None:
        """Verify src/web/dataset.html exists on disk."""
        self.assertTrue(
            self.dataset_exists,
            "src/web/dataset.html must exist as the unified Dataset Visualizer page",
        )

    def test_4_2_dataset_executive_kpi_summary_cards(self) -> None:
        """Verify dataset.html contains Executive KPI summary cards."""
        self.assertTrue(self.dataset_exists, "dataset.html missing")
        kpi_indicators = [
            "giao dịch",
            "mặt hàng",
            "tập phổ biến",
            "luật",
        ]
        lower_html = self.dataset_html.lower()
        for ind in kpi_indicators:
            self.assertIn(
                ind,
                lower_html,
                f"Dataset visualizer missing Executive KPI indicator for '{ind}'",
            )

    def test_4_3_dataset_tab1_frequent_itemsets_funnel(self) -> None:
        """Verify dataset.html contains visual section for Frequent Itemsets (L1 to L4)."""
        self.assertTrue(self.dataset_exists, "dataset.html missing")
        lower_html = self.dataset_html.lower()
        self.assertTrue(
            "tập phổ biến" in lower_html or "itemset" in lower_html,
            "Dataset visualizer missing Frequent Itemsets section",
        )
        self.assertTrue(
            "l1" in lower_html and "l4" in lower_html,
            "Dataset visualizer missing L1 to L4 level indicators",
        )

    def test_4_4_dataset_tab2_association_rules_explorer(self) -> None:
        """Verify dataset.html contains section for Association Rules ($A \Rightarrow B$)."""
        self.assertTrue(self.dataset_exists, "dataset.html missing")
        lower_html = self.dataset_html.lower()
        self.assertTrue(
            "luật kết hợp" in lower_html or "rule" in lower_html,
            "Dataset visualizer missing Association Rules Explorer",
        )
        self.assertTrue(
            "lift" in lower_html and "confidence" in lower_html,
            "Dataset visualizer missing Lift and Confidence indicators",
        )

    def test_4_5_dataset_visual_bar_charts(self) -> None:
        """Verify dataset.html contains visual horizontal bar progress charts."""
        self.assertTrue(self.dataset_exists, "dataset.html missing")
        lower_html = self.dataset_html.lower()
        has_bars = "bar-track" in lower_html or "bar-fill" in lower_html or "progress" in lower_html
        self.assertTrue(
            has_bars,
            "Dataset visualizer missing horizontal bar chart containers",
        )

    def test_4_6_dataset_clean_light_theme_and_data_fetch(self) -> None:
        """Verify dataset.html adopts Clean Light SaaS design and fetches /api/dataset-stats."""
        self.assertTrue(self.dataset_exists, "dataset.html missing")
        self.assertIn(
            "/api/dataset-stats",
            self.dataset_html,
            "dataset.html must fetch data from '/api/dataset-stats'",
        )
        lower_html = self.dataset_html.lower()
        has_light_theme = "#f8fafc" in lower_html or "#ffffff" in lower_html or "var(--bg" in lower_html
        self.assertTrue(has_light_theme, "dataset.html should adopt Clean Light styling")


class TestTier1Feature5GlobalNavbar(E2ETestBase):
    """Feature 5: Global Navigation Bar Consistency (>= 5 tests)."""

    def setUp(self) -> None:
        self.templates = {
            "index.html": self.load_template("index.html"),
            "shop.html": self.load_template("shop.html"),
            "dataset.html": self.load_template("dataset.html"),
        }

    def test_5_1_all_html_views_contain_navigation_header(self) -> None:
        """Verify all HTML views have a header element for global navigation."""
        required_views = ["index.html", "shop.html", "dataset.html"]
        for view in required_views:
            self.assertIn(
                view,
                self.templates,
                f"View template {view} missing from src/web",
            )
            content = self.templates[view]
            has_header = "<header" in content.lower() or "<nav" in content.lower()
            self.assertTrue(has_header, f"{view} missing <header> or <nav> navigation container")

    def test_5_2_all_views_link_to_shop_route(self) -> None:
        """Verify all templates include a link to the Storefront (/shop)."""
        for view, content in self.templates.items():
            self.assertTrue(
                'href="/shop"' in content or "href='/shop'" in content,
                f"{view} missing hyperlink to '/shop'",
            )

    def test_5_3_all_views_link_to_stepper_demo_route(self) -> None:
        """Verify all templates include a link to the Algorithm Stepper (/)."""
        for view, content in self.templates.items():
            has_root_link = (
                'href="/"' in content
                or "href='/'" in content
                or 'href="/index.html"' in content
            )
            self.assertTrue(has_root_link, f"{view} missing hyperlink to '/'")

    def test_5_4_all_views_link_to_dataset_route(self) -> None:
        """Verify all templates include a link to Dataset Visualizer (/dataset)."""
        for view, content in self.templates.items():
            self.assertTrue(
                'href="/dataset"' in content or "href='/dataset'" in content,
                f"{view} missing hyperlink to '/dataset'",
            )

    def test_5_5_legacy_redirects_for_stats_and_admin(self) -> None:
        """Verify legacy /stats and /admin URLs redirect to /dataset."""
        for path in ("/stats", "/admin"):
            status, headers, _ = self.get(path)
            self.assertEqual(status, 301, f"{path} should redirect with 301")
            self.assertEqual(headers.get("location"), "/dataset")

    def test_5_6_mobile_toggle_button_presence_for_responsive_navbar(self) -> None:
        """Verify templates contain a mobile menu toggle button for responsive viewports."""
        for view, content in self.templates.items():
            has_toggle = (
                "mobile" in content.lower()
                or "toggle" in content.lower()
                or "hamburger" in content.lower()
                or "menu" in content.lower()
            )
            self.assertTrue(
                has_toggle,
                f"{view} missing mobile navigation toggle button",
            )

    def test_5_6_mobile_toggle_button_presence_for_responsive_navbar(self) -> None:
        """Verify templates contain a mobile menu toggle button for responsive viewports."""
        for view, content in self.templates.items():
            has_toggle = (
                "mobile" in content.lower()
                or "toggle" in content.lower()
                or "hamburger" in content.lower()
                or "menu" in content.lower()
            )
            self.assertTrue(
                has_toggle,
                f"{view} missing mobile navigation toggle button",
            )


if __name__ == "__main__":
    unittest.main()
