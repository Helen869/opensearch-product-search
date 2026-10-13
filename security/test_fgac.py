#!/usr/bin/env python3
"""Verify FGAC: each seller sees ONLY their own docs, and NEVER the cost field.
Admin sees everything including cost. Stdlib only.
"""
import base64
import json
import ssl
import urllib.request

BASE = "https://localhost:9200"
CTX = ssl._create_unverified_context()


def search(user, password, size=100):
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    body = json.dumps({"query": {"match_all": {}}, "size": size}).encode()
    r = urllib.request.Request(BASE + "/products/_search", data=body, method="GET")
    r.add_header("Authorization", f"Basic {auth}")
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, context=CTX) as resp:
        return json.loads(resp.read())


def check(user, password, expect_sellers, expect_cost):
    data = search(user, password)
    hits = data["hits"]["hits"]
    sellers = {h["_source"]["seller"] for h in hits}
    has_cost = any("cost" in h["_source"] for h in hits)
    ok_sellers = sellers == expect_sellers
    ok_cost = has_cost == expect_cost
    print(f"{user}: {len(hits)} docs, sellers seen={sellers} "
          f"({'PASS' if ok_sellers else 'FAIL'}), cost visible={has_cost} "
          f"({'PASS' if ok_cost else 'FAIL'})")
    return ok_sellers and ok_cost


def main():
    results = [
        check("seller-a", "Seller123!", {"seller-a"}, False),
        check("seller-b", "Seller123!", {"seller-b"}, False),
        check("admin", "StrongPass123!", {"seller-a", "seller-b"}, True),
    ]
    print("ALL PASS" if all(results) else "SOME CHECKS FAILED — re-check setup_fgac.sh output")


if __name__ == "__main__":
    main()
