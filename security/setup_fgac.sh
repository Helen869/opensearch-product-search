#!/usr/bin/env bash
# FGAC setup: role + 2 seller users + role mapping, via the Security API.
# DLS limits each seller to their own documents; FLS hides the cost field.
# Run from the security/ directory. Cluster must be up (Step 1) first.
set -euo pipefail
BASE=https://localhost:9200
AUTH="admin:StrongPass123!"

echo "== role: seller_role (DLS on seller == user, FLS hides cost) =="
curl -sk -u "$AUTH" -X PUT "$BASE/_plugins/_security/api/roles/seller_role" \
  -H 'Content-Type: application/json' -d '{
  "cluster_permissions": ["cluster_composite_ops_ro"],
  "index_permissions": [{
    "index_patterns": ["products*"],
    "dls": "{\"term\": {\"seller\": \"${user.name}\"}}",
    "fls": ["~cost"],
    "allowed_actions": [
      "indices:data/read/search",
      "indices:data/read/get",
      "indices:data/read/mget",
      "indices:admin/mappings/get",
      "indices:admin/aliases/get"
    ]
  }],
  "tenant_permissions": [{
    "tenant_patterns": ["global_tenant"],
    "allowed_actions": ["kibana_all_read"]
  }]
}'
echo

for u in seller-a seller-b; do
  echo "== user: $u =="
  curl -sk -u "$AUTH" -X PUT "$BASE/_plugins/_security/api/internalusers/$u" \
    -H 'Content-Type: application/json' -d '{
    "password": "Seller123!",
    "backend_roles": ["seller"],
    "attributes": {}
  }'
  echo
done

echo "== role mapping: backend role 'seller' -> seller_role =="
curl -sk -u "$AUTH" -X PUT "$BASE/_plugins/_security/api/rolesmapping/seller_role" \
  -H 'Content-Type: application/json' -d '{
  "backend_roles": ["seller"],
  "users": []
}'
echo
echo "FGAC setup done. Run: python3 test_fgac.py"
