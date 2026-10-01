"""Exercise real HTTP requests without requiring third-party dependencies."""
import http.client
import json
import threading
import unittest

from app import AprioriRequestHandler, ThreadedHTTPServer
from src.data.sample_baskets import UI_PRESETS


class HTTPTests(unittest.TestCase):
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

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        body = json.dumps(payload) if payload is not None else None
        connection.request(method, path, body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    def test_index_and_shared_presets(self):
        status, data = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"fetch('/api/presets')", data)
        status, data = self.request("GET", "/api/presets")
        self.assertEqual(status, 200)
        presets = json.loads(data)
        self.assertEqual(presets["ui_presets"], UI_PRESETS)
        self.assertIn(presets["default"], presets["presets"])
        self.assertEqual(len(presets["ui_presets"]), 6)

    def test_both_analysis_endpoints(self):
        status, data = self.request("POST", "/api/apriori", {
            "transactions": [{"tid": "T1", "items": ["a", "b"]}],
            "min_count": 1, "min_confidence": .7,
        })
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["strong"], 2)
        status, data = self.request("POST", "/api/analyze", {
            "baskets": "a, b", "min_support": 1, "min_confidence": .7,
        })
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)["rules"]), 2)

    def test_invalid_json_shape_and_empty_transactions(self):
        for path in ("/api/analyze", "/api/apriori"):
            status, data = self.request("POST", path, [])
            self.assertEqual(status, 400)
            self.assertIn("JSON object", json.loads(data)["error"])
        status, data = self.request("POST", "/api/apriori", {"transactions": []})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(data))


if __name__ == "__main__":
    unittest.main()
