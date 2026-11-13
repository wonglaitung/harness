# harness-cli

Harness 的创作期/运维期命令行工具。运行时治理在 `harness-sdk` 里强制，
本包只负责治理块生成/校验、审批、Kill Switch 与依赖诊断。

版本与 `harness-sdk` 同步发布（依赖约束 `>=0.1,<0.2`），避免 CLI 的校验
规则与 SDK 运行时规则漂移。

```bash
pip install harness-cli          # 会同时安装 harness-sdk

harness governance init ./skills      # 生成并写入治理块（默认写入）
harness governance check ./skills/x.md
harness governance approve apr-0000 --actor alice
harness governance suspend agent-id --reason "人工复核"
harness doctor --deps
```

未安装时也可在仓库里直接运行：

```bash
cd packages/cli
PYTHONPATH=src:../sdk/src python -m harness_cli governance check ../sdk/skills/x.md
```
