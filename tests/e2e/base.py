"""Base test harness for Apriori E2E Test Suite.

Provides an in-process ThreadedHTTPServer on an ephemeral port, HTTP client helpers,
template inspection utilities, and simulation engines without third-party dependencies.
"""
from __future__ import annotations

import http.client
import json
import os
import sys
import threading
import unittest
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import AprioriRequestHandler, ThreadedHTTPServer

WEB_DIR = os.path.join(PROJECT_ROOT, "src", "web")
DATA_DIR = os.path.join(PROJECT_ROOT, "src", "data")
ECOM_RULES_PATH = os.path.join(DATA_DIR, "ecom_rules.json")
RETAIL_STATS_PATH = os.path.join(DATA_DIR, "retail_stats.json")


class E2ETestBase(unittest.TestCase):
    """Base class providing zero-dependency live HTTP server and assertion helpers."""

    server: ThreadedHTTPServer
    server_thread: threading.Thread
    port: int

    @classmethod
    def setUpClass(cls) -> None:
        """Start self-hosted HTTP server on an ephemeral OS-assigned port (port 0)."""
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), AprioriRequestHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        """Gracefully terminate background HTTP server."""
        try:
            cls.server.shutdown()
            cls.server.server_close()
            cls.server_thread.join(timeout=2.0)
        except Exception:
            pass

    def request(
        self,
        method: str,
        path: str,
        body: bytes | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], str]:
        """Execute HTTP request against the running ephemeral server."""
        req_headers = {"User-Agent": "Apriori-E2E-TestSuite/1.0"}
        if headers:
            req_headers.update(headers)

        if isinstance(body, str):
            encoded_body = body.encode("utf-8")
        elif isinstance(body, bytes):
            encoded_body = body
        else:
            encoded_body = None

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=encoded_body, headers=req_headers)
            response = conn.getresponse()
            status = response.status
            res_headers = {k.lower(): v for k, v in response.getheaders()}
            data = response.read().decode("utf-8", errors="replace")
            return status, res_headers, data
        finally:
            conn.close()

    def get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
        """Perform HTTP GET request."""
        return self.request("GET", path, headers=headers)

    def get_json(self, path: str) -> tuple[int, dict[str, str], Any]:
        """Perform HTTP GET and parse JSON response."""
        status, headers, text = self.get(path, headers={"Accept": "application/json"})
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        return status, headers, parsed

    def post_json(self, path: str, payload: Any) -> tuple[int, dict[str, str], Any]:
        """Perform HTTP POST with JSON body and parse response."""
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        status, res_headers, text = self.request("POST", path, body=body, headers=headers)
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        return status, res_headers, parsed

    @staticmethod
    def load_template(filename: str) -> str:
        """Read HTML template from src/web."""
        filepath = os.path.join(WEB_DIR, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Template file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def load_ecom_rules() -> dict[str, Any]:
        """Read src/data/ecom_rules.json."""
        if not os.path.exists(ECOM_RULES_PATH):
            raise FileNotFoundError(f"Data file not found: {ECOM_RULES_PATH}")
        with open(ECOM_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_retail_stats() -> dict[str, Any]:
        """Read src/data/retail_stats.json."""
        if not os.path.exists(RETAIL_STATS_PATH):
            raise FileNotFoundError(f"Data file not found: {RETAIL_STATS_PATH}")
        with open(RETAIL_STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def simulate_cascade_recommendations(
        cart_skus: list[str] | set[str],
        data: dict[str, Any],
        max_recom: int = 4,
    ) -> list[dict[str, Any]]:
        """Simulate the 4-tier cascade recommendation algorithm client-side.

        Tier 1: Mined association rules where antecedent is completely covered in cart.
        Tier 2: Partial overlap antecedent match.
        Tier 3: Frequent Combos L2.
        Tier 4: Store Bestsellers (L1 fallback).
        """
        in_cart = set(cart_skus)
        recommendations: list[dict[str, Any]] = []
        seen_targets: set[str] = set()

        rules = data.get("rules", [])
        combos = data.get("combos", [])
        catalog = data.get("catalog", {})

        # Tier 1: Full Antecedent Match
        if in_cart and rules:
            for r in rules:
                ant = r.get("antecedent", [])
                if ant and all(item in in_cart for item in ant):
                    for target in r.get("consequent", []):
                        if target not in in_cart and target not in seen_targets:
                            seen_targets.add(target)
                            recommendations.append({
                                "code": target,
                                "tier": 1,
                                "lift": r.get("lift", 1.0),
                                "confidence": r.get("confidence", 0.0),
                                "score": r.get("lift", 1.0) * 10 + r.get("confidence", 0.0),
                                "source": "exact_rule",
                            })

        # Tier 2: Partial Overlap Match
        if len(recommendations) < max_recom and in_cart and rules:
            for r in rules:
                ant = r.get("antecedent", [])
                if ant and any(item in in_cart for item in ant):
                    for target in r.get("consequent", []):
                        if target not in in_cart and target not in seen_targets:
                            seen_targets.add(target)
                            recommendations.append({
                                "code": target,
                                "tier": 2,
                                "lift": r.get("lift", 1.0),
                                "confidence": r.get("confidence", 0.0),
                                "score": r.get("lift", 1.0) * 5 + r.get("confidence", 0.0),
                                "source": "partial_rule",
                            })

        # Tier 3: Frequent Pairs (Combos L2)
        if len(recommendations) < max_recom and combos:
            for combo in combos:
                items = combo.get("items", [])
                if len(items) == 2:
                    a, b = items[0], items[1]
                    if a in in_cart and b not in in_cart and b not in seen_targets:
                        seen_targets.add(b)
                        recommendations.append({
                            "code": b,
                            "tier": 3,
                            "score": combo.get("count", 100),
                            "source": "combo_l2",
                        })
                    elif b in in_cart and a not in in_cart and a not in seen_targets:
                        seen_targets.add(a)
                        recommendations.append({
                            "code": a,
                            "tier": 3,
                            "score": combo.get("count", 100),
                            "source": "combo_l2",
                        })

        # Tier 4: Store Bestsellers (L1 fallback)
        if len(recommendations) < max_recom:
            # Check frequent_itemsets L1 first if available
            frequents_l1 = data.get("frequent_itemsets", {}).get("L1", [])
            candidate_skus = []
            if frequents_l1:
                candidate_skus = [entry["items"][0] for entry in frequents_l1 if entry.get("items")]
            if not candidate_skus:
                candidate_skus = ["85123A", "22423", "84879", "20725", "22720", "22383", "21212", "85099B"]

            for sku in candidate_skus:
                if sku not in in_cart and sku not in seen_targets and sku in catalog:
                    seen_targets.add(sku)
                    recommendations.append({
                        "code": sku,
                        "tier": 4,
                        "score": 1,
                        "source": "bestseller_l1",
                    })
                if len(recommendations) >= max_recom:
                    break

        recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)
        return recommendations[:max_recom]
