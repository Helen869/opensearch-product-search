#!/usr/bin/env python3
"""Generate 1000 fake products as bulk JSONL for OpenSearch.

Output: products.jsonl in this directory (bulk format: action line + doc line).
Deterministic (seed 42) so re-runs produce the same data.
"""
import json
import random

random.seed(42)

ADJECTIVES = ["Air", "Cloud", "Trail", "Urban", "Flex", "Pro", "Eco", "Swift"]
CATALOG = {
    "shoes": ["Sneakers", "Running Shoes", "Boots", "Sandals", "Loafers"],
    "laptops": ["Laptop", "Notebook Computer", "Ultrabook", "Gaming Laptop"],
    "furniture": ["Couch", "Sofa", "Desk", "Bookshelf", "Office Chair"],
    "audio": ["Headphones", "Earphones", "Speaker", "Soundbar"],
    "kitchen": ["Blender", "Coffee Maker", "Air Fryer", "Toaster"],
}
TAGS = ["new", "bestseller", "eco", "clearance", "limited"]


def one_product(i):
    category = random.choice(list(CATALOG))
    name = f"{random.choice(ADJECTIVES)} {random.choice(CATALOG[category])}"
    price = round(random.uniform(15, 800), 2)
    stock = 0 if random.random() < 0.08 else random.randint(1, 500)
    return {
        "product_id": f"P-{i:04d}",
        "name": name,
        "description": f"{name} for everyday use. Durable, lightweight, and built for {category}.",
        "category": category,
        "seller": "seller-a" if random.random() < 0.55 else "seller-b",
        "price": price,
        "cost": round(price * random.uniform(0.4, 0.7), 2),
        "stock": stock,
        "rating": round(random.uniform(3.0, 5.0), 1),
        "tags": random.sample(TAGS, k=random.randint(1, 2)),
        "created_at": f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
    }


def main():
    with open("products.jsonl", "w", encoding="utf-8") as f:
        for i in range(1, 1001):
            doc = one_product(i)
            f.write(json.dumps({"index": {"_index": "products-v1", "_id": doc["product_id"]}}) + "\n")
            f.write(json.dumps(doc) + "\n")
    print("Wrote 1000 products to products.jsonl")


if __name__ == "__main__":
    main()
