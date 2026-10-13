# Mini Product Search on OpenSearch — R&P 面试小项目

**目标**：用一天时间，亲手搭一个电商产品搜索引擎，覆盖 R&P 下一轮的六个 OpenSearch 考点：FGAC、cluster、index、version migration、security index、triage alert。面试时讲"我上周刚搭的"，不是"我听说过"。

**诚实说明**：这个骨架是在没有 Docker 的环境里写的，**没有实际跑通过**。如果某一步报错，把报错发出来调。

## 前置要求

- Docker + Docker Compose（本地跑，零云成本）
- 内存：留 4GB 给 Docker
- Linux：先跑 `sudo sysctl -w vm.max_map_count=262144`（否则 OpenSearch 起不来）；Mac / Windows Docker Desktop 一般不用
- Python 3（只用标准库，不用 pip 装东西）
- 密码：admin / `StrongPass123!`，seller 账号密码 `Seller123!`（演示用，别用在真环境）

## 跑法（按顺序，6 步）

### Step 1 — Cluster：起 2 节点集群

```bash
docker compose up -d
curl -ku admin:StrongPass123! https://localhost:9200/_cat/health
```

期望：两个节点，状态先 yellow（副本未分配）→ 变成 green。Dashboards：http://localhost:5601（admin 登录）。
面试线：*"I ran a 2-node cluster, watched it go yellow then green, and used _cat/shards to see replica allocation."*

### Step 2 — Index：建索引 + 灌数据

```bash
cd seed
python3 generate_products.py     # 生成 1000 条假商品数据 -> products.jsonl
python3 setup_index.py           # 建 products-v1（mapping + 数据 + alias）
```

`index-mapping.json` 里看三个关键设计：`name` 是 text（分词）+ keyword 子字段（精确匹配）+ autocomplete 子字段（edge n-gram）；`category`/`seller` 是 keyword；同义词 filter（sneakers = running shoes）。
面试线：*"I used explicit mappings — text for search, keyword for filters — and an alias so I can reindex with zero downtime."*

### Step 3 — FGAC + Security index：配权限

```bash
cd ../security
bash setup_fgac.sh               # 建 role + 两个 seller 用户 + role mapping
python3 test_fgac.py             # 验证：seller-a 只能看自己商品、看不到 cost 字段
```

原理：role `seller_role` 用 DLS（`{"term": {"seller": "${user.name}"}}`）限定文档范围，用 FLS（`~cost`）隐藏成本字段；配置存在系统 index `.opendistro_security` 里，改配置走 Security API，**不要直接手写那个 index**。
面试线：*"I mapped IdP-style backend roles to OpenSearch roles, used DLS for per-seller visibility and FLS to hide cost. The config lives in the .opendistro_security index."*

### Step 4 — Triage alert：配告警并触发一次

```bash
cd ../alerting
# 先去 https://webhook.site 拿一个临时 URL（不用注册），再跑：
WEBHOOK_URL=https://webhook.site/你的ID python3 setup_alerting.py
python3 trigger_alert.py         # 再灌 120 条零库存商品，触发告警
```

Monitor 每分钟查一次"零库存商品 > 50 件"就告警到 webhook。触发后按 `triage-runbook.md` 走一遍：确认 → 影响 → 止血 → 根因 → 跟进。
面试线：*"I set up a monitor, fired it on purpose, and triaged it with a runbook — verify, impact, stop the bleeding, root cause, follow-up."*

### Step 5 — Version migration：2.x → 3.x

```bash
cd ../migration
bash snapshot.sh                 # v2 集群拍快照到共享目录
docker compose -f ../docker-compose-v3.yml up -d   # 起 v3 集群（端口 9202 / 5602）
python3 restore.py               # v3 上 restore → reindex 到 products-v2 → alias 切换 → 验证
```

流程：查 breaking changes → staging 演练 → 快照 → restore → 验证查询结果一致 → alias 切换；旧集群保留 = rollback。
面试线：*"I migrated 2.x to 3.x with snapshot/restore, reindexed with a mapping change, switched the alias, and kept the old cluster for rollback."*

### Step 6 — 验证全部

```bash
cd ..
python3 verify.py
```

## 清理

```bash
docker compose down -v
docker compose -f docker-compose-v3.yml down -v
```

## 排障

| 现象 | 可能原因 |
|---|---|
| 容器起不来 / bootstrap checks failed | `vm.max_map_count` 太低（见前置要求） |
| 镜像 pull 失败 | 把 compose 里的 `2.19.1` 换成 `2`，`3.0.0` 换成 `3`（major tag） |
| 快照注册报 "not in path.repo" | `path.repo` 环境变量没生效：进容器确认，或改用挂载的 `opensearch.yml` |
| seller 登录 Dashboards 看不到数据 | 租户权限 / DLS 配错，先跑 `test_fgac.py` 定位 |
| 告警没触发 | Monitor 是每分钟跑一次，等 1–2 分钟；确认零库存商品真的 > 50 件 |

## 文件结构

```
docker-compose.yml        v2 双节点集群 + Dashboards（9200 / 5601）
docker-compose-v3.yml     v3 单节点集群 + Dashboards（9202 / 5602，迁移目标）
seed/                     数据生成 + 建索引脚本 + mapping
security/                 FGAC 配置 + 验证脚本
alerting/                 告警 monitor 配置 + 触发脚本 + triage runbook
migration/                快照 + restore/reindex/alias 切换
verify.py                 一键验证
```
