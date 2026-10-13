#!/usr/bin/env bash
# Migration Step A: snapshot the v2 cluster into the shared ./snapshots directory.
# Run from the migration/ directory. v2 cluster (port 9200) must be up.
set -euo pipefail
BASE=https://localhost:9200
AUTH="admin:StrongPass123!"

echo "== register filesystem repo (shared ./snapshots) =="
curl -sk -u "$AUTH" -X PUT "$BASE/_snapshot/demo_repo" \
  -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": {"location": "demo_repo", "compress": true}
}'
echo

echo "== snapshot products-v1 =="
curl -sk -u "$AUTH" -X PUT "$BASE/_snapshot/demo_repo/snap-v1?wait_for_completion=true" \
  -H 'Content-Type: application/json' -d '{
  "indices": "products-v1",
  "ignore_unavailable": true,
  "include_global_state": false
}'
echo
echo "Snapshot done. Next: docker compose -f ../docker-compose-v3.yml up -d"
