"""Storefront data, pages, and HTTP route invariants."""
from __future__ import annotations

import http.client
import json
import os
import threading
import unittest

from app import AprioriRequestHandler, ThreadedHTTPServer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_PATH = os.path.join(PROJECT_ROOT, "src", "data", "store.json")
RULES_PATH = os.path.join(PROJECT_ROOT, "src", "data", "ecom_rules.json")
WEB_DIR = os.path.join(PROJECT_ROOT, "src", "web")


class StorefrontDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STORE_PATH, encoding="utf-8") as handle:
            cls.store = json.load(handle)
        with open(RULES_PATH, encoding="utf-8") as handle:
            cls.rules = json.load(handle)

    def test_catalog_join_preserves_canonical_keys(self):
        self.assertEqual(len(self.store["categories"]), 18)
        self.assertEqual(len(self.store["catalog"]), 169)
        self.assertEqual(set(self.store["catalog"]), set(self.rules["catalog"]))
        self.assertIn("whole milk", self.store["catalog"])
        self.assertEqual(self.store["catalog"]["whole milk"]["display_name"], "whole milk")
        for entry in self.store["catalog"].values():
            self.assertIsInstance(entry["price"], int)
            self.assertGreater(entry["price"], 0)
            self.assertIn(entry["category"], {c["id"] for c in self.store["categories"]})

    def test_combos_use_l2_l3_and_expected_discount(self):
        self.assertEqual(len(self.store["combos"]), 12)
        self.assertEqual(len(self.store["bestsellers"]), 10)
        self.assertNotIn("shopping bags", self.store["bestsellers"])
        first = self.store["combos"][0]
        self.assertEqual(first["items"], ["flour", "sugar"])
        self.assertEqual(first["count"], 49)
        self.assertEqual(first["lift"], 8.46)
        self.assertEqual(first["original_price"], 49000)
        self.assertEqual(first["price"], 44000)
        self.assertEqual(first["saving"], 5000)
        self.assertEqual(first["discount"], 10)
        for combo in self.store["combos"]:
            self.assertIn(len(combo["items"]), (2, 3))
            self.assertGreaterEqual(combo["count"], 40)
            self.assertGreaterEqual(combo["lift"], 1.8)
            self.assertEqual(combo["saving"], combo["original_price"] - combo["price"])

    def test_combos_do_not_repeat_an_item_more_than_twice(self):
        uses = {}
        for combo in self.store["combos"]:
            for item in combo["items"]:
                uses[item] = uses.get(item, 0) + 1
        self.assertTrue(all(count <= 2 for count in uses.values()))


class StorefrontHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), AprioriRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", path)
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    def test_store_api_and_new_pages(self):
        status, data = self.get("/api/store")
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertEqual(len(payload["catalog"]), 169)
        self.assertEqual(len(payload["categories"]), 18)
        self.assertEqual(len(payload["combos"]), 12)

        for path in ("/cart", "/checkout"):
            status, data = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(b"G9", data)
            self.assertIn(b"store-cart.js", data)

    def test_shop_keeps_required_drawer_contract(self):
        status, data = self.get("/shop")
        self.assertEqual(status, 200)
        text = data.decode("utf-8")
        for needle in ("cart-drawer", "openCartDrawer", "/api/store", "/api/ecom-rules", "store-recs.js"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
