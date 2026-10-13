#!/usr/bin/env python3
"""Migration Step B: restore the 2.x snapshot into the 3.x cluster, reindex
with a mapping change, switch the alias, verify. Run AFTER snapshot.sh and
after `docker compose -f ../docker-compose-v3.yml up -d`.

Rollback (if anything looks wrong): point the alias back at products-v1:
  POST _aliases {"actions": [{"remove": {"index": "products-v2", "alias": "products"}},
                              {"add": {"index": "products-v1", "alias": "products"}}]}
Stdlib only.
"""
import base64
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

BASE = "https://localhost:9202"  # v3 cluster
AUTH = base64.b64encode(b"admin:StrongPass123!").decode()
CTX = ssl._create_unverified_context()


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Authorization", f"Basic {AUTH}")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, context=CTX) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:400]}")
        raise


def wait_for_index(index, timeout=120):
    for _ in range(timeout // 5):
        try:
            health = req("GET", f"/_cat/indices/{index}?format=json")
            if health and health[0]["status"] in ("green", "yellow"):
                return True
        except urllib.error.HTTPError:
            pass
        time.sleep(5)
    return False


def main():
    print("v3 cluster:", req("GET", "/")["version"]["number"])

    # 1. Register the SAME repo (shared ./snapshots volume)
    req("PUT", "/_snapshot/demo_repo", {
        "type": "fs", "settings": {"location": "demo_repo", "compress": True},
    })
    print("repo registered on v3")

    # 2. Restore products-v1 from the 2.x snapshot
    req("POST", "/_snapshot/demo_repo/snap-v1/_restore", {
        "indices": "products-v1",
        "ignore_unavailable": True,
        "include_global_state": False,
    })
    print("restore started...")
    if not wait_for_index("products-v1"):
        print("restore timed out — check _cat/recovery")
        sys.exit(1)
    v1_count = req("GET", "/products-v1/_count")["count"]
    print(f"restored products-v1 on v3: {v1_count} docs")

    # 3. Reindex into products-v2 with a mapping change (add discount field)
    with open("../seed/index-mapping.json", encoding="utf-8") as f:
        mapping = json.load(f)
    mapping["mappings"]["properties"]["discount"] = {"type": "float"}
    try:
        req("DELETE", "/products-v2")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    req("PUT", "/products-v2", mapping)
    req("POST", "/_reindex?wait_for_completion=true", {
        "source": {"index": "products-v1"},
        "dest": {"index": "products-v2"},
    })
    req("POST", "/products-v2/_refresh")
    v2_count = req("GET", "/products-v2/_count")["count"]
    print(f"reindexed products-v2: {v2_count} docs (v1 had {v1_count})")
    assert v1_count == v2_count, "count mismatch after reindex!"

    # 4. Alias switch: products -> products-v2 (zero downtime)
    req("POST", "/_aliases", {"actions": [
        {"remove": {"index": "products-v1", "alias": "products"}},
        {"add": {"index": "products-v2", "alias": "products"}},
    ]})
    print("alias 'products' now -> products-v2")
    alias_count = req("GET", "/products/_count")["count"]
    print(f"verify via alias: {alias_count} docs")
    print("Migration done. Old index products-v1 kept on v3 = instant rollback.")


if __name__ == "__main__":
    main()
