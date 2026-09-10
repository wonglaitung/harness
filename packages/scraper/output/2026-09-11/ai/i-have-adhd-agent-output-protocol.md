# i-have-adhd — Agent输出协议新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次将Agent输出格式作为独立标准化层。定义了"Action-first, No preamble"的Agent响应协议，开创了"Agent Human Factors"新类别 |
| 采用广度 | ☆☆☆☆/5 | 3,854 stars（单日），被多个Agent生态（Claude Code、Codex、OpenCode、Hermes）原生集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月10日发布（GitHub trending单日#1） |
| 社区热度 | ☆☆☆☆☆/5 | 3,854 stars today（GitHub Python trending #1），多语言翻译（中/日/韩/葡/越/泰），社区自发传播极强 |
| **总体判断** | ✅ | **新范式 — "Agent如何说话"成为第一优先级工程问题** |

## 技术定义 (What)

i-have-adhd 是第一个系统化的 **Agent响应格式协议**。它不是告诉Agent做什么，而是定义Agent如何说话——10条规则将Agent输出从"冗长、模糊、礼貌过度"重塑为"行动优先、步骤编号、无套话"。

核心协议（10条规则）：
1. **Action First** — 第一句话就是下一步操作
2. **Number Steps** — 多步骤任务用编号
3. **One Next Step** — 以具体下一步结束
4. **Suppress Tangents** — 不展开无关话题
5. **Restate State** — 每轮重述当前状态
6. **Specific Times** — 用"3分钟"而非"一会儿"
7. **Make Wins Visible** — 让进展可感知
8. **Matter-of-Fact Errors** — 错误不绕弯子
9. **Cap Lists at 5** — 清单最多5项
10. **No Preamble, No Recap, No Closers** — 不要"Great question!"、"Hope this helps!"

## 行业痛点 (Why)

AI Coding Agent的一个关键人机交互问题：Agent倾向于输出冗长、礼貌但低信息密度的回复。用户需要滚动翻过"Great question! Let me think about this..."才能找到真正要执行的命令。这在长时间编码会话中累积巨大的认知摩擦。

## 旧范式 vs 新范式
- **旧做法**：Agent自由发挥输出格式——"Great question! Let me think... Here's one approach... Hope this helps! Let me know if..."
- **新做法**：标准化Agent输出协议——立即给出可执行命令，步骤编号，零套话，以具体下一步收尾

> Before: "Great question! Looking at src/auth.ts, the verifyToken function seems to be using an older API. One approach would be to update the package..."
> After: "Run `npm install jsonwebtoken@latest`, then edit `src/auth.ts:42`. 1. Open src/auth.ts 2. Replace verifyToken (lines 42-58) 3. Run npm test"

## 生产力影响 (How)
- **信息密度提升**：Agent回复从200-300词压缩到50-80词的核心可执行内容
- **认知负荷降低**：无需从礼貌用语中提取行动
- **标准化接口**：不同Agent输出格式统一，降低切换成本
- **人机协作效率**：更接近"pair programming同事"的沟通风格

## 采用成本
- 安装：`claude plugin install i-have-adhd` 或复制 SKILL.md
- 学习曲线：零，安装即生效
- 兼容性：Claude Code、Codex、OpenCode、Hermes、Cursor等
- 可定制：Fork + 修改 SKILL.md 即可

## 采用案例
- Claude Code 原生集成：安装后所有Agent回复立即格式化
- Codex Skills Catalog 收录
- OpenCode 社区推荐插件
- 多语言社区自发翻译（7种语言README）

## 风险/局限
- 适用范围：主要面向Coding Agent场景，对话式AI不适用
- 过度简洁风险：在需要深入解释的复杂场景可能信息不足
- 非技术用户可能不适应极简输出风格

## 核心线索
- GitHub：https://github.com/ayghri/i-have-adhd
- Stars：3,854 today（Python trending #1）
- 发布时间：2026年9月
- 当前状态：活跃，社区极速增长