# harness-cli

Harness 的创作期/运维期命令行工具。运行时治理在 `harness-sdk` 里强制，
本包只负责治理块生成/校验、审批、Kill Switch 与依赖诊断。

版本与 `harness-sdk` 同步发布（依赖约束 `>=0.1,<0.2`），避免 CLI 的校验
规则与 SDK 运行时规则漂移。

```bash
pip install harness-cli          # 会同时安装 harness-sdk

harness governance init ./skills      # 生成并写入治理块（默认写入）
harness governance draft ./skills     # LLM 生成初稿（workflow 等），需人工确认
harness governance check ./skills/x.md
harness governance approve apr-0000 --actor alice
harness governance suspend agent-id --reason "人工复核"
harness doctor --deps
```

`draft` 的边界：

- 只生成草稿：`approved_by` / `owners` / `agent_id` / `version` 永不由模型决定；
- 草稿必须通过 `check` 同源的确定性校验才会写入；未填完 `TODO` 前 `check` 仍拒绝；
- 只做 completion、不执行工具；技能正文按不可信数据处理；
- 默认调用模型并写入，`--dry-run` 预览，`--emit-prompt` 只输出提示词（不联网）；
- provider/model/base_url 可用 `--provider` / `--model` / `--base-url` 或
  环境变量指定（默认 openai）。

### 接入 OpenAI 兼容网关

```bash
export HARNESS_LLM_PROVIDER=openai
export HARNESS_LLM_BASE_URL=https://your-gateway.example/v1
export HARNESS_LLM_MODEL=your-model
export HARNESS_LLM_API_KEY=sk-...
harness governance draft ./skills
```

- `HARNESS_LLM_BASE_URL` 要带版本前缀（如 `/v1`），与 OpenAI SDK 的
  `base_url` 语义一致；
- API key 也可用 `OPENAI_API_KEY`；不建议写在命令行参数里，避免进入 shell 历史；
- 也兼容 SDK 的 `HARNESS_PROVIDER` / `HARNESS_MODEL` / `HARNESS_BASE_URL`。

未安装时也可在仓库里直接运行：

```bash
cd packages/cli
PYTHONPATH=src:../sdk/src python -m harness_cli governance check ../sdk/skills/x.md
```
