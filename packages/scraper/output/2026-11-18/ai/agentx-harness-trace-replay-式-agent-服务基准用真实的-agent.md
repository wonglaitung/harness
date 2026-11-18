# AgentX Harness — Trace-Replay 式 Agent 服务基准

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把服务基准的输入从「合成 prompt」换成「真实 agent 轨迹」，并明确按 agent 数量而非请求数做并发扫描；评测对象从模型迁移到整个服务栈 |
| 采用广度 | ☆☆☆/5 | RunAnywhere（TrnRT）已据此发布 Trainium 结果并称「此前无公开 AgentX on Trainium」；SemiAnalysis 自有 InferenceX 平台配套数据集；基于 aiperf 分叉，兼容上游 |
| 时间新鲜 | ☆☆☆/5 | 1.0.7 版本，2026-11 在跑；无精确首发日 |
| 社区热度 | ⚠️☆☆/5 | 尚未进入 HN 主贴讨论，热度主要来自推理基础设施圈内 |
| **总体判断** | ⚠️ | **观察中——评测范式方向正确，但社区渗透尚早** |

## 技术定义（What）

AgentX Harness 是 SemiAnalysis 发布的推理服务基准工具（`pip install agentx-harness`），回放从大规模真实 agent 使用中采集的会话轨迹：百万级长上下文、多轮、子 agent、约 95% 输入命中前缀缓存。它不测「模型聪不聪明」，只测「服务在真实 agent 负载下的延迟、吞吐与每请求成本」。

## 行业痛点（Why）

此前推理服务的性能数字来自合成负载：固定输入长度、泊松到达、无缓存复用。真实 coding agent 的负载形态完全相反——长而高度重复的前缀、随子 agent 分支、用户逐轮等待。用合成长度测出的 tokens/s 无法回答「我这台机器能同时服务几个 agent」。

## 旧范式 vs 新范式

- **旧做法**：合成 prompt（固定 sequence length、随机到达）+ 报告 tokens/s 与 TTFT 均值，不区分缓存命中与新增 token
- **新做法**：轨迹回放；按 agent 数做并发扫描；分离报告输出/未缓存输入/缓存输入；成本折算到「每 agent 请求美元」

## 生产力影响（How）

让跨硬件栈可比。已知结论：Trainium2 单框 32 agent = 28.9 req/min、$0.021/请求；且暴露真实瓶颈——16 agent 以上开始排队等 decode 槽位，而非吞吐饱和。这直接影响「一台机器能挂几个 agent」的容量规划。

## 采用成本

低。pip 安装 + 单命令对接任何 OpenAI 兼容端点。但每个数据点需跑 1 小时，需要多并发配置才能稳定；数据集由 SemiAnalysis 分发。

## 风险/局限

- **自跑非官方**：第三方（RunAnywhere）自称「self-run，非官方 InferenceX 结果」，跨厂商数字未必同口径
- **轨迹偏差**：数据来自特定客户群的 agent 使用，偏 coding agent 形态，对 chat/RAG 负载代表性弱
- **点估计噪声**：每点单次运行，无置信区间
- **与上游 aiperf 分叉**：不能与上游同装，生态有割裂风险

## 核心线索

- GitHub：https://github.com/SemiAnalysisAI/agentx-harness
- 数据集：https://inferencex.semianalysis.com/datasets
- 发布时间：2026 年 11 月在用（v1.0.7）
- 当前状态：活跃，早期
