#!/usr/bin/env python3
"""One-shot verification: cluster health, index count, alias, FGAC.
Run from the project root after Steps 1-3. Stdlib only.
"""
import base64
import json
import ssl
import urllib.request

BASE = "https://localhost:9200"
CTX = ssl._create_unverified_context()


def req(method, path, user="admin", password="StrongPass123!", body=None):
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Authorization", f"Basic {auth}")
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, context=CTX) as resp:
        return json.loads(resp.read() or b"{}")


def main():
    ok = True

    health = req("GET", "/_cat/health?format=json")[0]
    print(f"cluster: {health['cluster']} status={health['status']} nodes={health['node.total']}")
    ok &= health["status"] in ("green", "yellow")

    count = req("GET", "/products-v1/_count")["count"]
    print(f"products-v1 docs: {count}")
    ok &= count >= 1000

    alias = req("GET", "/_alias/products")
    print(f"alias 'products' -> {list(alias)}")
    ok &= "products-v1" in alias or "products-v2" in alias

    data = req("GET", "/products/_search",
               user="seller-a", password="Seller123!",
               body={"query": {"match_all": {}}, "size": 100})
    sellers = {h["_source"]["seller"] for h in data["hits"]["hits"]}
    has_cost = any("cost" in h["_source"] for h in data["hits"]["hits"])
    print(f"FGAC seller-a: sellers={sellers}, cost visible={has_cost}")
    ok &= sellers == {"seller-a"} and not has_cost

    print("VERIFY: ALL PASS" if ok else "VERIFY: SOMETHING FAILED")


if __name__ == "__main__":
    main()
