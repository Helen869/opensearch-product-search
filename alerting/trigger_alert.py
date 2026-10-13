#!/usr/bin/env python3
"""Index 120 extra zero-stock products so the out-of-stock monitor fires.
Run after setup_alerting.py, then watch webhook.site + Dashboards Alerting.
Stdlib only.
"""
import base64
import json
import ssl
import urllib.request

BASE = "https://localhost:9200"
AUTH = base64.b64encode(b"admin:StrongPass123!").decode()
CTX = ssl._create_unverified_context()


def main():
    lines = []
    for i in range(120):
        doc = {
            "product_id": f"TRIG-{i:03d}",
            "name": "Trigger Product",
            "description": "Zero-stock product to fire the alert.",
            "category": "shoes",
            "seller": "seller-a",
            "price": 9.99,
            "cost": 5.0,
            "stock": 0,
            "rating": 4.0,
            "tags": ["clearance"],
            "created_at": "2026-10-13",
        }
        lines.append(json.dumps({"index": {"_index": "products-v1", "_id": doc["product_id"]}}))
        lines.append(json.dumps(doc))
    r = urllib.request.Request(BASE + "/_bulk", data=("\n".join(lines) + "\n").encode(), method="POST")
    r.add_header("Authorization", f"Basic {AUTH}")
    r.add_header("Content-Type", "application/x-ndjson")
    with urllib.request.urlopen(r, context=CTX) as resp:
        result = json.loads(resp.read())
    assert not result.get("errors"), "bulk errors"
    r2 = urllib.request.Request(BASE + "/products-v1/_refresh", data=b"", method="POST")
    r2.add_header("Authorization", f"Basic {AUTH}")
    urllib.request.urlopen(r2, context=CTX)
    print("Indexed 120 zero-stock docs. Monitor runs every minute — check webhook.site.")


if __name__ == "__main__":
    main()
