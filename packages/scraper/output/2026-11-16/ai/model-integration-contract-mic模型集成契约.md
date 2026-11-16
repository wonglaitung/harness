# Model Integration Contract (MIC，模型集成契约)

## 技术定义 (What)
由 Hugging Face 提出的模型测试打包标准，一份契约 = ①fixture（从真实 checkpoint 按配置等比缩小、但保留全部层类型的「微缩模型」，并原样保留 tokenizer/processor）+ ②usage path（可运行的 Markdown 用法示例）+ ③baselines（人工审核过的期望输出）。只要 usage path 在 fixture 上跑出的结果仍等于 baselines，契约即成立。核心思想是「架构 + 用法」而非「单一权重」作为被测单元。

## 行业痛点 (Why)
Transformers 支持 750+ 模型类型、88,000+ CPU 测试与 200,000+ GPU 测试/天。真实 checkpoint 集成测试太重，无法在每个 PR 上跑，导致回归只能靠每日定时任务事后发现——UMT5 的 attention 越界 bug（decoder 能看到未来 token）在 main 上存活了近两个月，且「仅仅跑一次 forward」根本发现不了。

## 旧范式 vs 新范式
- **旧做法**：PR 上只跑轻量单元测试与手工挑的小配置，真模型集成测试留给每日 GPU 长跑；或各集成方各自维护一套 tiny-random-* 小模型，标准不一、只验证「能否加载 + forward 不崩」。
- **新做法**：把「大模型」压成可提交到 CI 的「微缩契约」：Llama 4 Scout 从 108.6B 参数缩到 44.7M（UMT5 fixture 66MB vs 源 1,227MB），每次 PR 只按改动文件挑选相关 MIC，在便宜 CPU runner 上 13.4 秒完成验证，并能回放历史 commit 定位 bug 引入点。LLM 负责起草契约，人类负责批准 baseline——「LLM 起草，不负责签字」。

## 生产力影响 (How)
把模型回归的发现时间从「数周后」压缩到「合并前」；让超大模型（装不进标准 GPU runner）也能进入日常 CI；为模型维护者提供了可复用、可版本锁定（fleet dataset 固定 revision）的测试资产。

## 采用成本
中等：需要 CLI `tmic` + 一次 fixture 构建与 baseline 人工审核（可本地 --local-only 先跑）；每新增架构需按四步配方 shrink 配置（保留 sliding/full attention、dense/MoE 等层类型多样性）。

## 核心线索
- GitHub：https://github.com/huggingface/transformers-mic
- 来源：https://huggingface.co/blog/transformers-mic
- 发布时间：2026-11-16
