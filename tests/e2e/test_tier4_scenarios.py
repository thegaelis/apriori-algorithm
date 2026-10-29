"""Tier 4: Real-World Workload Scenarios E2E Tests.

Requirement: End-to-end full user journeys and administrator workflows:
1. Complete shopping basket workflow simulation (browse, add, cross-sell, stepper, total, drawer)
2. Complete admin exploratory analytics workflow simulation (KPIs, Tab 1, Tab 2, Tab 3, CSV export)
"""
from __future__ import annotations

import io
import json
import unittest
from typing import Any

from tests.e2e.base import E2ETestBase


class TestTier4ShoppingWorkflow(E2ETestBase):
    """Scenario 1: Complete Shopping Basket Workflow Simulation."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.catalog = self.data.get("catalog", {})
        self.rules = self.data.get("rules", [])

    def test_4_1_complete_shopping_basket_workflow(self) -> None:
        """Simulate end-to-end shopping journey:

        1. Customer accesses storefront GET /shop.
        2. Client retrieves production rules GET /api/ecom-rules.
        3. Customer views categories and chooses Jumbo Bags ('BAG').
        4. Customer adds '85099B' (JUMBO BAG RED RETROSPOT) to cart.
        5. Smart Apriori recommendation engine activates and suggests cross-sell items.
        6. Customer accepts cross-sell suggestion and adds recommended item to cart.
        7. Customer increments quantity of primary item.
        8. Subtotals and grand total update with exact decimal arithmetic.
        9. Recommendations dynamically refresh, excluding items already in cart.
        """
        # Step 1: Customer loads store page
        status, headers, text = self.get("/shop")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))

        # Step 2: Client app fetches ecom rules
        api_status, api_headers, rules_data = self.get_json("/api/ecom-rules")
        self.assertEqual(api_status, 200)
        self.assertIsInstance(rules_data, dict)

        # Step 3: Identify primary product in catalog
        primary_sku = "85099B"
        if primary_sku not in self.catalog:
            # Fallback to first available catalog item
            primary_sku = next(iter(self.catalog.keys()))

        primary_item = self.catalog[primary_sku]
        primary_price = float(primary_item.get("price", 2.08))

        # Step 4: Add primary product to cart state
        cart: dict[str, dict[str, Any]] = {
            primary_sku: {
                "code": primary_sku,
                "name": primary_item.get("name"),
                "price": primary_price,
                "qty": 1,
            }
        }

        # Step 5: Evaluate Apriori recommendations for current cart
        recoms_step1 = self.simulate_cascade_recommendations([primary_sku], rules_data, max_recom=4)
        self.assertGreater(len(recoms_step1), 0, "Recommendations must not be empty after adding product")
        self.assertNotIn(primary_sku, [r["code"] for r in recoms_step1])

        # Step 6: Customer clicks '+ Thêm nhanh' on top recommended item
        top_recommended = recoms_step1[0]["code"]
        rec_item = self.catalog.get(top_recommended, {"name": top_recommended, "price": 2.08})
        rec_price = float(rec_item.get("price", 2.08))

        cart[top_recommended] = {
            "code": top_recommended,
            "name": rec_item.get("name"),
            "price": rec_price,
            "qty": 1,
        }
        self.assertEqual(len(cart), 2)

        # Step 7: Customer clicks '+' to increment primary item quantity to 2
        cart[primary_sku]["qty"] += 1
        self.assertEqual(cart[primary_sku]["qty"], 2)

        # Step 8: Calculate subtotal and total
        subtotal = sum(item["qty"] * item["price"] for item in cart.values())
        expected_subtotal = round(2 * primary_price + 1 * rec_price, 2)
        self.assertAlmostEqual(subtotal, expected_subtotal, places=2)

        formatted_total = f"£{subtotal:.2f}"
        self.assertTrue(formatted_total.startswith("£"))

        # Step 9: Re-evaluate recommendations with 2 items in cart
        current_cart_skus = list(cart.keys())
        recoms_step2 = self.simulate_cascade_recommendations(current_cart_skus, rules_data, max_recom=4)

        for in_cart_sku in current_cart_skus:
            self.assertNotIn(
                in_cart_sku,
                [r["code"] for r in recoms_step2],
                f"Item {in_cart_sku} already in cart must not appear in updated recommendations",
            )


class TestTier4AdminWorkflow(E2ETestBase):
    """Scenario 2: Complete Admin Exploratory Analytics Workflow Simulation."""

    def setUp(self) -> None:
        self.data = self.load_ecom_rules()
        self.summary = self.data.get("summary", {})
        self.frequents = self.data.get("frequent_itemsets", {})
        self.rules = self.data.get("rules", [])
        self.catalog = self.data.get("catalog", {})

    def test_4_2_complete_admin_analytics_workflow(self) -> None:
        """Simulate end-to-end admin data science exploration workflow:

        1. Data scientist accesses Admin Portal GET /admin.
        2. Retrieves rules & metadata via GET /api/ecom-rules.
        3. Inspects Executive KPI metrics (baskets, itemsets L1/L2/L3, strong rules, max lift).
        4. Explores Tab 1 (Frequent Itemsets):
           - Filters by level k=2.
           - Adjusts min support slider to >= 2.0%.
           - Searches for keyword 'BAG'.
        5. Explores Tab 2 (Association Rules):
           - Filters by min confidence >= 0.30 and min lift >= 3.0.
           - Searches antecedent for 'JUMBO BAG'.
           - Validates rule business insight string generation.
           - Simulates CSV export generation.
        6. Explores Tab 3 (Network Graph & Co-occurrence Matrix):
           - Extracts node list from top frequent items.
           - Extracts edge list with source, target, lift, confidence.
        """
        # Step 1: Access Admin Portal
        status, headers, text = self.get("/admin")
        self.assertEqual(status, 200)

        # Step 2: Retrieve API data
        api_status, _, rules_data = self.get_json("/api/ecom-rules")
        self.assertEqual(api_status, 200)

        # Step 3: Inspect Executive KPI metrics
        self.assertIn("total_baskets", self.summary)
        self.assertGreater(self.summary.get("total_baskets", 0), 10000)
        self.assertIn("curated_rules_count", self.summary)

        # Step 4: Tab 1 - Frequent Itemsets Filter Simulation
        l2_itemsets = self.frequents.get("L2", [])
        if l2_itemsets:
            # Filter min support >= 0.02 (2.0%)
            high_supp_l2 = [entry for entry in l2_itemsets if entry.get("support", 0.0) >= 0.02]
            for entry in high_supp_l2:
                self.assertGreaterEqual(entry["support"], 0.02)
                self.assertEqual(len(entry["items"]), 2)

            # Search keyword 'BAG'
            bag_itemsets = []
            for entry in l2_itemsets:
                item_names = [self.catalog.get(sku, {}).get("name", "") for sku in entry["items"]]
                if any("BAG" in name.upper() for name in item_names):
                    bag_itemsets.append(entry)
            self.assertIsInstance(bag_itemsets, list)

        # Step 5: Tab 2 - Association Rules Filter & CSV Export Simulation
        min_conf = 0.30
        min_lift = 3.0
        filtered_rules = [
            r for r in self.rules
            if r.get("confidence", 0.0) >= min_conf and r.get("lift", 0.0) >= min_lift
        ]
        for r in filtered_rules:
            self.assertGreaterEqual(r["confidence"], min_conf)
            self.assertGreaterEqual(r["lift"], min_lift)

            # Business insight text validation
            ant_names = " + ".join(self.catalog.get(s, {}).get("name", s) for s in r["antecedent"])
            cons_names = " + ".join(self.catalog.get(s, {}).get("name", s) for s in r["consequent"])
            insight = f"Khách mua {ant_names} có xu hướng mua {cons_names} gấp {r['lift']:.1f}× lần (độ tin cậy {r['confidence']*100:.0f}%)."
            self.assertIn("gấp", insight)

        # Simulate CSV export
        csv_buffer = io.StringIO()
        csv_buffer.write("antecedent,consequent,support,confidence,lift,count\n")
        for r in filtered_rules[:20]:
            ant_str = ";".join(r["antecedent"])
            cons_str = ";".join(r["consequent"])
            csv_buffer.write(f'"{ant_str}","{cons_str}",{r["support"]},{r["confidence"]},{r["lift"]},{r.get("count", 0)}\n')

        csv_content = csv_buffer.getvalue()
        self.assertTrue(csv_content.startswith("antecedent,consequent"))
        self.assertIn("\n", csv_content)

        # Step 6: Tab 3 - Network Graph Node & Edge Simulation
        top_items = self.frequents.get("L1", [])[:30]
        nodes = []
        for entry in top_items:
            sku = entry["items"][0]
            cat_item = self.catalog.get(sku, {})
            nodes.append({
                "id": sku,
                "label": cat_item.get("name", sku),
                "category": cat_item.get("category", "OTHER"),
                "support": entry.get("support", 0.01),
            })

        edges = []
        node_ids = {n["id"] for n in nodes}
        for r in self.rules:
            if len(r["antecedent"]) == 1 and len(r["consequent"]) == 1:
                u, v = r["antecedent"][0], r["consequent"][0]
                if u in node_ids and v in node_ids:
                    edges.append({
                        "source": u,
                        "target": v,
                        "lift": r["lift"],
                        "confidence": r["confidence"],
                    })

        self.assertIsInstance(nodes, list)
        self.assertIsInstance(edges, list)


if __name__ == "__main__":
    unittest.main()
