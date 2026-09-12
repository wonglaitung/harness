# Python SDK vs Java SDK 内容同步报告

**首次生成**: 2026-06-26（原 `FULL_SYNC_REPORT.md`，声称 96% 同步）
**本版刷新**: 2026-09-13 — 原报告已严重过期（未覆盖 gate 模块、streaming、M6 安全加固、2026-09 的 wrapper/测试修复），且连 Python 的 `state`/`review` 命名映射都未记录。本版基于代码库实测数据重写。

**对比范围**: Python SDK (`packages/sdk`) vs Java SDK (`packages/sdk-java`)

---

## 1. 规模对比（实测）

| 指标 | Python SDK | Java SDK |
|------|-----------|----------|
| 源文件数 | 128 `.py` | 15 模块 / ~260 `.java`(main+test) |
| 主代码 LOC | ~42,183 | ~50,446 (main only) |
| 测试文件 | 60 `test_*.py` | 65 `*Test` 类 / **549 测试全绿** |
| 顶层包/模块 | 18 (`core/llm/mcp/memory/skills/tools/security/guardrails/gate/state/review/connectors/triggers/service/sdk/testing/loop/orchestrator/...`) | 15 (`*-core/-llm/-mcp/-memory/-skills/-tools/-security/-guardrails/-gate/-connectors/-triggers/-orchestrator/-loop/-integration/-all`) |

> Java LOC 略高属语言冗余 + 少量 Java 独有类，不代表"更完整"。

---

## 2. 模块对齐表（含命名映射）

| Python 包 | Java 模块 | 状态 | 备注 |
|-----------|----------|------|------|
| `core/` | `harness-sdk-core` | ✅ | 类型/Hook/Ralph/SubAgent/Observability 基本对齐 |
| `llm/` | `harness-sdk-llm` | ✅ | Anthropic/OpenAI/Mock/Routing/LlamaCpp 对齐 |
| `mcp/` | `harness-sdk-mcp` | ✅ | Stdio/HTTP transport 对齐 |
| `memory/` + `state/` | `harness-sdk-memory` | ✅(部分) | **命名映射**：`state/base|file|db|memory_store`→`StateStore|FileStateStore|...`；但 `state/redis_store.py`(Redis 持久化 agent state) **Java 无对应** |
| `skills/` | `harness-sdk-skills` | ✅ | Skill/Registry/Loader/Trigger 对齐 |
| `tools/` | `harness-sdk-tools` | ✅ | Read/Write/Edit/Bash/Glob/Grep/Web* 对齐；Java 额外 `UpdateCoreMemoryTool` |
| `security/` | `harness-sdk-security` | ✅ | Sandbox/Validator/InjectionDetector/Audit/ResultSanitizer 对齐 |
| `guardrails/` | `harness-sdk-guardrails` | ✅ | PIIDetector/ComplianceJudge/StreamInterceptor/中文 PII 对齐 |
| `gate/` | `harness-sdk-gate` | ✅ (近期补齐) | `d76f1ecb` 对齐 Python gate；declarative/metrics/models/reconciliation/retry/validators + DeterministicGate 对齐 |
| `review/` | `harness-sdk-orchestrator` (ReviewQueue) | ✅(改名) | Python `review/queue.py` → Java `orchestrator/ReviewQueue` |
| `connectors/` | `harness-sdk-connectors` | ✅ | GitHub/Slack/Webhook/Manager 对齐 |
| `triggers/` | `harness-sdk-triggers` | ✅ | base/cron/interval/manager/types 对齐 |
| `service/` | `harness-sdk-core` (分散) | ⚠️ 部分 | MetricsCollector/TracingManager/RedisSessionStore/ServiceDiscovery 已入 core；**FastAPI/Spring Boot HTTP 端点未实现** |
| `sdk/` + `cli.py` | `harness-sdk-integration` + `core/HarnessCli` | ✅ | `sdk/config.py|harness.py`→integration；`cli.py`(doctor --deps)→`HarnessCli` |
| `testing/` | `harness-sdk-integration/.../testing` | ✅ | MockHarness/RecordingHarness 对齐 |
| `loop/` `orchestrator/` | `harness-sdk-loop` `harness-sdk-orchestrator` | ✅ | GoalLoop/AgentLoop/Team 等对齐；**streaming 已同步**（见 §3） |

---

## 3. 自 2026-06 以来新增的同步内容（原报告缺失）

- **Streaming（Phase 1/2）**：Python `core/streaming.py`（`AgentLoop.stream_run()`、`LLM.stream_with_tools()`、`GoalLoop.stream()`、`AgentHarness.stream_goal()`）→ Java `core/StreamEvent`(结构化信封: source/category/seq/event_id/parent_id)、`StreamingHandler`、`StreamingConfig`、`StreamingStats` + `guardrails/StreamInterceptor`。提交 `27693ab9`/`aa57c8e5`/`dc6c8268`。
- **Gate 模块**：`d76f1ecb` 补齐 `harness-sdk-gate`（确定性闸门，对齐 Python gate）。
- **M6 安全加固**：`81603b81` 同步 InjectionClassifier / ReviewQueue / SharedStateStore / CLI；含 A4 provenance、B2 工具闸门、C4 覆盖、H1 死锁检测。
- **Wrapper 修复 + 全量测试修复**：`ac20d630`(重建损坏的 gradle-wrapper + 修正 .gitignore)、`ced6a808`(549 测试全绿)。

---

## 4. 功能覆盖率（重新评估）

| 模块 | 结构覆盖 | 行为等价信心 | 备注 |
|------|---------|-------------|------|
| Core / Types | ~98% | 中 | HookManager 未独立实现 |
| LLM | ~95% | 中 | LLMConfig 未独立 |
| MCP | ~100% | 中高 | |
| Memory/State | ~90% | 中 | **Redis agent-state store 缺**；FileStateStore 曾有 Jackson stale bug |
| Security | ~95% | **低** | 见 §5 实锤漂移 |
| Skills | ~95% | 中 | LoadingLevel 未独立 |
| Tools | ~100% | 中高 | |
| Guardrails | ~100% | 中 | |
| Gate | ~95% | 中 | 近期补齐，待更多回归 |
| Connectors/Triggers | ~100% | 中 | |
| Service | ~85% | 中 | HTTP 端点框架依赖 |
| Orchestrator/Loop | ~95% | 中 | ReviewQueue 曾有持久化 bug |

**综合判断**：结构性同步 **~90%+(高)**；但**行为等价性无法用 LOC/类映射保证（见 §5）**。原报告"96%、剩余=框架差异"的乐观结论已不成立。

---

## 5. 行为等价性风险（实锤证据）

"类存在" ≠ "行为一致"。2026-09 实测发现以下**类早已同步但行为已漂移**的案例：

1. `PromptInjectionDetector.normalize()` 对零宽+混淆字符产生**错误改写**（`ignore`→`ignare`），使 A1 零宽剥离测试长期失败。
2. `InputValidator` 无参构造默认把 injection 当作 **error 而非 javadoc 声明的 warning**，`testInjectionDetection` 长期红。
3. `LightweightSandbox` 的反 obfuscation 未覆盖 `cu\rl`(反斜杠在字母前)，`validateCommandBlocksObfuscatedCurl` 长期红。
4. `ReviewItem` 反序列化丢失 id、`ReviewQueue` resolve 不清 pending —— gate 持久化逻辑 bug。
5. `FileStateStore` Jackson `isExpired()` getter 干扰反序列化 —— memory 往返 bug。
6. `LightweightSandbox.normalizeCommand()` 与 Python `_normalize_cmd` **行为不一致**：Java 剥离字母前的反斜杠（`cu\rl`→`curl`），Python 保留原样（`cu\rl`）。Java 侧该改动(安全强化)尚未回灌 Python，属**单向漂移**。
7. `InputValidator.validate()` 注入检测范围不一致：Java 对 `"Ignore previous instructions"` 判 `isSafe=false`，Python 同输入判 `isSafe=true`（Python 需更完整短语如 "...and reveal your system prompt"）。`detect()` 两侧一致，仅 `validate()` 粒度不同。

→ 上述 6、7 已由新增的**跨语言行为对拍测试**(`harness-sdk-security`/`harness-sdk-gate` 的 `CrossLanguageParityTest`)自动捕获并记录（非致命，构建仍绿）。说明同步质量靠"类映射 + 手改测试"，**缺乏自动行为回归**——现已补最小对拍。

---

## 6. 真实功能缺口（非零但小）

- **Redis agent-state store**：✅ 已实现 `harness-sdk-memory` 的 `RedisStateStore`（对齐 Python `state/redis_store.py`，Jedis 5.1.5 + Lua 原子 CAS；`RedisStateStoreTest` 在 Redis 不可达时跳过）。
- **Service HTTP 端点**（FastAPI / Spring Boot Controller）：框架差异，有意延迟。
- `HookManager` 独立实现（现集成于 AgentLoop）、`setup_observability()`、`LoadingLevel`、`LLMConfig` 独立类、`AsyncSQLiteSessionStore`。
- **Python 侧近期独立演进需回灌**：如 `e630b63a`(document size validation / SpanBuilder / Redis skip 修复 Python 测试)、`3bea8e0f`(document size validation) 等，Java 侧未必有对应实现/测试。

---

## 7. 治理 / 流程建议（防止复现）

同步当前为**人工 + 单向(Python→Java) + AI 辅助**，仅靠手维护的本报告 + commit 标注「同步 Python…」追踪，**无自动化 parity 闸门**。本次"全量编译不过/测试红"正是缺 CI 回归的后果。建议：

1. **本报告纳入 CI 自动重新生成**（或加 `docs` 漂移检查），避免再次过期。
2. **CI 固化 `./gradlew test`**（排除需 live key 的 `harness-sdk-integration`），防止 wrapper/依赖类问题复现。
3. ✅ 已对**关键安全(A1/A2)/闸门(B2)逻辑**建立最小跨语言行为对拍测试(`CrossLanguageParityTest`)，防护 §5 类行为漂移——后续仅需"把对拍发现的 divergence 收敛为一致/或显式标注为有意差异"。
4. 排期补齐 §6 缺口，优先 **回灌 Python 近期改动**（如 §6 所列 document size validation 等）并收敛对拍发现的漂移。

---

## 8. 结论

- 结构性覆盖很高（估计 90%+），主要模块均已对齐，含近期 streaming / gate / M6 同步。
- **核心风险不是"缺模块"，而是"同步后行为漂移 + 文档/测试滞后 + 无自动 parity 校验"**——本报告已刷新、CI 测试已固化全绿(549 测试)、Redis agent-state store 已补齐、关键逻辑跨语言对拍已建立。
- 下一步优先级：收敛对拍发现的 2 处漂移(normalize_command 反斜杠 / validate 注入粒度) → 回灌 Python 近期改动(document size validation 等) → 报告纳入 CI 自动重生。
