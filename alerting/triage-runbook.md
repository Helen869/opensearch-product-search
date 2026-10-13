# Alert Triage Runbook（告警分流处置流程）

面试时如果问 "triage alert"，按这五步讲——每一步都要有动作，不是光说概念。

## 1. Verify（确认是真的）

- 告警本身可能是误报：查原始指标。JVM 告警 → 看 `_cat/nodes` 的 heap 和 GC；延迟告警 → 看查询延迟是不是真涨了。
- 问：是持续的，还是 1 分钟毛刺？单点还是全集群？

## 2. Impact（判断影响面）

- 搜索受影响吗？索引写入受影响吗？影响的是所有用户还是某个 seller / 某个 index？
- 定 severity：P1（搜索不可用）/ P2（变慢）/ P3（只是噪音）。

## 3. Stop the bleeding（先止血）

- 降负载：限流、关掉 heavy aggregation 查询、清 cache。
- 扩容量：加 data node、或把副本数临时调高。
- **先恢复服务，再找根因。** 顺序不能反。

## 4. Root cause（根因）

- 常见根因：坏查询（全表扫、超大 aggregation）、shard 不均衡、磁盘水位、版本 bug、数据量自然增长。
- 证据：slow log、hot threads、shard 分布、GC 日志。

## 5. Follow-up（跟进闭环）

- 调 monitor：阈值、分级、runbook 链接，让下次告警直接可操作。
- 防告警疲劳：阈值太松 → 噪音 → 人开始忽略 → 真出事没人看。宁可少而准。

## 本项目里的实演

Monitor `out-of-stock-surge`：零库存商品 > 50 件 → webhook 告警。
触发后走一遍：确认（查 `stock <= 0` 的 count 是不是真 > 50）→ 影响（只是业务告警，不是集群故障，P3）→ 止血（本例不用，业务告警）→ 根因（trigger 脚本灌了 120 条零库存数据）→ 跟进（删掉 TRIG-* 测试数据，或把阈值调高）。

## 英文样例（JVM 告警 triage）

> "First I verify — check _cat/nodes for heap usage and GC, and whether query latency actually went up. If it's real, I check impact: is indexing or search degraded? To stop the bleeding I can reduce load or scale out. Then root cause: a bad query, a shard imbalance, or just growth. Follow-up is tuning the monitor — severity, threshold, and runbook link — so the next alert is actionable, not just noise."
