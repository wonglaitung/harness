# Scry

## 新范式评分
| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | 5/5 | "互联网超立方体"+程序式查询，明确声称无同类 MCP 支持 |
| 采用广度 | 2/5 | open alpha，社区早期 |
| 时间新鲜 | 5/5 | 2026-09 open alpha + Show HN |
| 社区热度 | 2/5 | Show HN 60 points（另 HN 讨论提及） |
| 总体判断 | ✅ | 新范式（概念性强，早期） |

## 数据规模
- 总计 ≈1669 亿行，含 Social 33.7B、Web 75.9B、Scholarship 9.37B、Code 43.9B、Markets/Records 等。
- 20 个未披露来源 262B 行（占 61%）。

## 典型查询能力
- 聚合 Reddit/Twitter/HN/arXiv/OpenAlex/预测市场等，支持 hasAnyTokens、GROUP BY、JOIN、时间过滤、排序。
- 示例：找出"被保存但没被点赞的 coding agent 推文"、"谁和谁在 HN 上反复争吵"、"同时引用 Scaling Laws 和 Chinchilla 的论文"。

## 风险/局限
- 托管产品非开源，依赖供应商。
- 查询语言有学习曲线，数据覆盖缺口可能导致"空结果"误读。