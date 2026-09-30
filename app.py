from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
from typing import Any

from src.core.apriori import analyze_baskets, parse_baskets, format_itemset, format_rule, build_apriori_trace
from src.data.sample_baskets import PRESET_BASKETS, DEFAULT_PRESET_NAME

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "src", "web")
INDEX_PATH = os.path.join(WEB_DIR, "index.html")


def serialize_analysis_result(analysis: dict[str, Any]) -> dict[str, Any]:
    """Ensure all frozensets and tuples in analysis result are JSON-serializable."""
    serialized_frequents = [
        [sorted(list(itemset)), round(supp, 4), count]
        for itemset, supp, count in analysis.get("frequent_itemsets", [])
    ]

    serialized_rules = [
        {
            "antecedent": sorted(list(r["antecedent"])),
            "consequent": sorted(list(r["consequent"])),
            "support": round(r["support"], 4),
            "confidence": round(r["confidence"], 4),
            "lift": round(r["lift"], 4),
        }
        for r in analysis.get("rules", [])
    ]

    return {
        "transaction_count": analysis.get("transaction_count", 0),
        "min_support": analysis.get("min_support", 0.0),
        "min_confidence": analysis.get("min_confidence", 0.0),
        "min_support_count": analysis.get("min_support_count", 0),
        "transactions": analysis.get("transactions", []),
        "all_unique_items": analysis.get("all_unique_items", []),
        "training_steps": analysis.get("training_steps", []),
        "frequent_itemsets": serialized_frequents,
        "rules": serialized_rules,
    }


class AprioriRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Zero-dependency self-hosted HTTP handler for the Apriori Training App."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self.serve_index()
        elif self.path == "/api/presets":
            self.send_json({
                "default": DEFAULT_PRESET_NAME,
                "presets": PRESET_BASKETS,
            })
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/analyze":
            self.handle_analyze()
        elif self.path == "/api/apriori":
            self.handle_apriori_trace()
        else:
            self.send_error(404, "Endpoint Not Found")

    def serve_index(self) -> None:
        """Serve the single-page application index.html."""
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                content = f.read().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading index.html: {e}")

    def handle_analyze(self) -> None:
        """Process basket data through Apriori and return full educational trace."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            payload = json.loads(body_bytes.decode("utf-8"))

            baskets_text = payload.get("baskets", "")
            min_support = float(payload.get("min_support", 0.4))
            min_confidence = float(payload.get("min_confidence", 0.7))

            transactions = parse_baskets(baskets_text)
            analysis = analyze_baskets(transactions, min_support, min_confidence)
            response_data = serialize_analysis_result(analysis)

            self.send_json(response_data)
        except Exception as e:
            self.send_json({"error": str(e)}, status=400)

    def handle_apriori_trace(self) -> None:
        """Run the step-by-step Apriori trace used by the interactive web UI."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            payload = json.loads(body_bytes.decode("utf-8"))

            transactions = payload.get("transactions", [])
            min_count = max(1, int(payload.get("min_count", 1)))
            min_confidence = float(payload.get("min_confidence", 0.6))

            if not transactions:
                raise ValueError("Cần ít nhất một giao dịch để phân tích.")

            trace = build_apriori_trace(transactions, min_count, min_confidence)
            self.send_json(trace)
        except Exception as e:
            self.send_json({"error": str(e)}, status=400)

    def send_json(self, data: Any, status: int = 200) -> None:
        """Utility method to send JSON responses."""
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        if args and str(args[1]) in ("200", "304"):
            return
        super().log_message(format, *args)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded HTTP Server for non-blocking concurrent requests."""
    daemon_threads = True
    allow_reuse_address = True


def start_server(preferred_ports: list[int] | None = None) -> None:
    if preferred_ports is None:
        preferred_ports = [8000, 8080, 5000, 7860, 8888]

    cli_port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    env_port = int(os.environ.get("PORT", 0)) if os.environ.get("PORT", "").isdigit() else None
    ports_to_try = [p for p in [cli_port, env_port] if p] + preferred_ports

    server = None
    active_port = None

    for port in ports_to_try:
        try:
            server = ThreadedHTTPServer(("0.0.0.0", port), AprioriRequestHandler)
            active_port = port
            break
        except OSError:
            continue

    if server is None or active_port is None:
        print("ERROR: Could not bind server to any candidate port.")
        sys.exit(1)

    print("=" * 60)
    print("  Apriori Market Basket Analysis - Self-Hosted Web Server")
    print("=" * 60)
    print(f"  Status: RUNNING (Zero third-party dependencies)")
    print(f"  Local URL:   http://localhost:{active_port}")
    print(f"  Network URL: http://127.0.0.1:{active_port}")
    print("=" * 60)
    print("  Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    start_server()
