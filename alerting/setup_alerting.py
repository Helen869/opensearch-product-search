#!/usr/bin/env python3
"""Create a webhook destination + an out-of-stock monitor via the Alerting API.

Usage:
  WEBHOOK_URL=https://webhook.site/<your-id> python3 setup_alerting.py
Get a free throwaway URL at https://webhook.site (no signup).
Stdlib only.
"""
import base64
import json
import os
import ssl
import sys
import urllib.request

BASE = "https://localhost:9200"
AUTH = base64.b64encode(b"admin:StrongPass123!").decode()
CTX = ssl._create_unverified_context()


def req(method, path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method=method)
    r.add_header("Authorization", f"Basic {AUTH}")
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, context=CTX) as resp:
        return json.loads(resp.read() or b"{}")


def main():
    url = os.environ.get("WEBHOOK_URL", "")
    if not url or "REPLACE-ME" in url or "webhook.site" not in url:
        print("Set WEBHOOK_URL first: get a free URL at https://webhook.site")
        print("  WEBHOOK_URL=https://webhook.site/<your-id> python3 setup_alerting.py")
        sys.exit(1)

    dest = req("POST", "/_plugins/_alerting/destinations", {
        "type": "custom_webhook",
        "name": "demo-webhook",
        "custom_webhook": {"url": url, "header_params": {"Content-Type": "application/json"}},
    })
    dest_id = dest["id"]
    print(f"destination created: {dest_id}")

    monitor = req("POST", "/_plugins/_alerting/monitors", {
        "name": "out-of-stock-surge",
        "type": "monitor",
        "monitor_type": "query_level_monitor",
        "enabled": True,
        "schedule": {"period": {"interval": 1, "unit": "MINUTES"}},
        "inputs": [{"search": {
            "indices": ["products-v1"],
            "query": {"size": 0, "query": {"range": {"stock": {"lte": 0}}}},
        }}],
        "triggers": [{
            "query_level_trigger": {
                "name": "too-many-out-of-stock",
                "severity": "2",
                "condition": {"script": {
                    "source": "ctx.results[0].hits.total.value > 50",
                    "lang": "painless",
                }},
                "actions": [{
                    "name": "notify-webhook",
                    "destination_id": dest_id,
                    "message_template": {
                        "source": "Out-of-stock surge: {{ctx.results.0.hits.total.value}} products at zero stock."
                    },
                    "throttle_enabled": False,
                }],
            }
        }],
    })
    print(f"monitor created: {monitor['_id']}")
    print("Fire it: python3 trigger_alert.py, then watch webhook.site within 1-2 minutes.")


if __name__ == "__main__":
    main()
