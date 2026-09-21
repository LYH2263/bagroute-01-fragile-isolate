# BagRoute

投递装袋：按路线订户顺序装袋，重量与体积双约束，超限拒收；易碎站点隔离装袋。

## 装袋规则

1. 按现网路线 `seq` 顺序装袋，重量与体积双约束任一超限即满额开新袋。
2. **易碎隔离**：订户点可标记为易碎（站点页勾选并落库）。易碎站点与非易碎站点
   绝不装进同一袋——即使当前袋重量、体积都还够，易碎性切换也必须新开袋
   （开袋原因记为 `fragile`，区别于满额开袋 `full`）。
3. 单站自身已超路线重量/体积限额时，仍走现网拒收（`over_limit`），
   不能借隔离规则装进任何袋。
4. 装袋页与袋明细用「仅易碎 / 仅非易碎」标签区分；拒收页把超限拒收与
   满额/易碎隔离开新袋分两栏展示。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4300 |
| API | http://localhost:9300 |
| API 文档 | http://localhost:9300/docs |
| Postgres | localhost:5444 |

健康检查：`GET http://localhost:9300/api/health`

## 页面

- `/routes` — 路线
- `/stops` — 订户点
- `/pack` — 装袋
- `/bags` — 袋明细
- `/rejects` — 拒收
- `/weights` — 袋重

## 使用说明

1. 查看路线与订户点顺序。
2. 在装袋页选择路线执行双约束装袋。
3. 袋明细与袋重查看结果，拒收页查看超限订户。

## 开发与测试

```bash
docker compose exec api pytest -q
```
