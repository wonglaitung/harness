# ffmpeg-skill — SPEC（Self-Producing Execution Contract）契约自生产

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确提出并命名 **SPEC**：`input_schema` 在运行时由定义 CLI 的同一个 argparse parser 派生，CI 检测漂移。解题对象是 Agent 工具生态普遍存在的"四份手写契约互相腐化" |
| 采用广度 | ☆☆/5 | 已被同一作者的 9 个兄弟 skill（video-editing / remotion / transcription / subtitle / color-grading / qc…）作为底层引擎读取 `contract --json` 与 `--json` 输出，形成单向依赖 |
| 时间新鲜 | ☆☆☆☆/5 | v3 新项目；FFmpeg 6.1/7.1/8/9 全在 CI 测试矩阵内 |
| 社区热度 | ☆☆☆☆/5 | GitHub Python trending **331 stars/day**；npm 发布；OpenSSF Scorecard；MIT |
| **总体判断** | ✅ | **新范式（Agent 工具契约层）** |

## 技术定义 (What)

`ffmpeg-skill` 是一个 Agent Skill（给 Claude Code / Cursor / Codex / 任意读 `SKILL.md` 的 Agent 用），教会 Agent 一条固定工作流：**probe（先测）→ 尽可能无损编辑 → check（量指标）→ verify（交付前复验）**。

它附 42 个真正干活的工具（基于 ffmpeg / ffprobe）：剪切、拼接、静音移除、按时长/画幅适配、字幕与卡拉OK、叠加与动效、HDR→SDR 与 LUT、音频清理与类型化动态处理、带漂移校正的音画同步、多机位、响度、交付检查、整片工程渲染、批量目录。每个工具同时是 MCP tool；默认向客户端只广告 12 个核心工具以省上下文，`FFMPEG_SKILL_MCP_FULL=1` 列出全部 42 个。

**SPEC 内核**：每个工具的 `input_schema`（契约中必须与 CLI flag 逐一对齐的部分）从不手写，而是运行时从已定义 CLI 的 argparse parser 派生；CI 一旦发现漂移即构建失败。

## 行业痛点 (Why)

两层痛点：

1. **Agent 会猜**：不懂基础设施就会假设参数 —— 猜帧率、选容器不支持的编码、对只需 stream copy 的文件重编码、不验证就说 done
2. **Agent 工具契约会腐化**：SKILL.md 描述、MCP schema、CLI `--help`、实际代码是四份独立维护的手写物，长期必然漂移。Agent 按 schema 调用却打到不存在的 flag，是最难 debug 的一类 Agent 故障

## 旧范式 vs 新范式

- **旧做法**：手写 schema + 手写文档 + 手写帮助文本，靠人保持同步；Agent 编辑完自评成功
- **新做法**：schema 单点派生（argparse 是唯一真相源，CI 守漂移）+ 输出强制被测量（`check.py` / `look.py` 给出结构化 JSON 指标）
- **副产物**：CLI / MCP / Skill 三个暴露面天然一致，因为它们都从同一个 parser 长出来

## 生产力影响 (How)

- 写 Agent 工具的人：省掉"三份文档同步"的长期税，工具即可靠契约
- 剪视频的人：全本地离线，素材不必上传；42 个工具覆盖从剪切到交付 QC 的完整链路
- 生态正确性：文档承诺"每个 before/after demo 都由 `python3 demos/build.py` 生成"，可自行重建每一帧 —— 演示不可伪造

## 采用成本

- `npx ffmpeg-skill` 即用；仅需 PATH 上有 ffmpeg + python3（只用标准库，无依赖安装）
- 无 API key、无账号、无云
- 上下文成本可调：默认 12 工具，需全量再开 42

## 采用案例

- **同作者生态**：`remotion-ffmpeg-skill` 的 composition 直接取本仓库 `probe.py` / `silence.py` / `scenes.py` 的时长、fps、帧、静音点、场景切点、音频峰值与节拍，并用 `check.py` / `look.py` 验证渲染、`overlay.py --place` 合成图形层、`render.py --template` 交付
- **9 个兄弟 skill** 以 `contract --json` / `--json` 输出 / `doctor` 为本仓库的消费接口，依赖单向、无回环

## 风险/局限

- **能力边界**：只做"手"不做"脑" —— 不决定剪哪里、不判断交付是否可批准、不改写字幕文案（用户 cue 文本原样烧入）
- **依赖 FFmpeg 版本**：虽测 6.1/7.1/8/9，但跨越旧版本可能缺 filter
- **SPEC 适用范围**：本项目用 Python argparse 得以"parser 即真相源"；其他语言/框架（如 Rust clap、Go cobra）需各自实现派生器才能复用该范式
- **单人维护**：作者生态高度集中，bus factor 偏低

## 核心线索

- GitHub：https://github.com/kajisho5/ffmpeg-skill
- 官网/演示：https://kajisho5.github.io/ffmpeg-skill/ ・ docs/demos.md
- npm：https://www.npmjs.com/package/ffmpeg-skill
- 首发来源：GitHub Python trending daily（2026-11-16），331 stars today
- 当前状态：活跃（CI + Scorecard + Sponsor）
- 许可：MIT
