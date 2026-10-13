#!/usr/bin/env python3
"""Create products-v1 with explicit mapping, bulk-load data, attach alias.

Stdlib only. Run from the seed/ directory after `python3 generate_products.py`.
"""
import base64
import json
import ssl
import sys
import urllib.error
import urllib.request

BASE = "https://localhost:9200"
AUTH = base64.b64encode(b"admin:StrongPass123!").decode()
CTX = ssl._create_unverified_context()  # demo certs are self-signed


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Authorization", f"Basic {AUTH}")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, context=CTX) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:500]}")
        raise


def main():
    # 0. Cluster reachable?
    print("cluster:", req("GET", "/")["cluster_name"])

    # 1. Fresh index (delete if exists from a previous run)
    try:
        req("DELETE", "/products-v1")
        print("deleted existing products-v1")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        print("no existing products-v1, creating fresh")

    with open("index-mapping.json", encoding="utf-8") as f:
        mapping = json.load(f)
    req("PUT", "/products-v1", mapping)
    print("created products-v1 with explicit mapping")

    # 2. Bulk load in batches of 200 docs (400 lines)
    with open("products.jsonl", encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i in range(0, len(lines), 400):
        chunk = "\n".join(lines[i:i + 400]) + "\n"
        r = urllib.request.Request(BASE + "/_bulk", data=chunk.encode(), method="POST")
        r.add_header("Authorization", f"Basic {AUTH}")
        r.add_header("Content-Type", "application/x-ndjson")
        with urllib.request.urlopen(r, context=CTX) as resp:
            result = json.loads(resp.read())
        if result.get("errors"):
            print("bulk errors in batch", i // 400)
            sys.exit(1)
    print(f"bulk-loaded {len(lines) // 2} docs")

    # 3. Alias: products -> products-v1 (zero-downtime reindex later)
    req("POST", "/_aliases", {"actions": [{"add": {"index": "products-v1", "alias": "products"}}]})
    print("alias \x27products\x27 -> products-v1")

    # 4. Verify
    req("POST", "/products-v1/_refresh")
    count = req("GET", "/products-v1/_count")["count"]
    print(f"verify: products-v1 has {count} docs")


if __name__ == "__main__":
    main()
