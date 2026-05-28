# 12 - 技术决策与权衡

## 概述

本文档记录 Harness 项目的技术决策、权衡取舍，以及已知限制和应对策略。

## 关键技术决策

### ADR-004: 长会话扩展性设计

**问题**: 会话消息可能持续增长，全量加载会导致内存爆炸。

**决策**: 采用分片存储 + 滑动窗口 + 分层摘要策略。

```
会话存储结构：
┌─────────────────────────────────────────────────────────┐
│ Session                                                 │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Active Window (最近 50 条消息)                   │   │
│  │ - 全量存储在内存                                 │   │
│  │ - 快速访问                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Recent Summaries (摘要层)                        │   │
│  │ - 每 100 条消息生成一个摘要                       │   │
│  │ - 存储在 SQLite，按需加载                        │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Archive (归档层)                                 │   │
│  │ - 原始消息压缩存储                               │   │
│  │ - 仅在需要时解压                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**实现**:

```python
class ScalableSessionStore:
    """可扩展的会话存储"""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_tables()

        # 配置
        self.active_window_size = 50      # 内存中保留的消息数
        self.summary_chunk_size = 100     # 每多少条生成摘要
        self.archive_threshold = 500      # 超过此数量开始归档

    async def get_session(self, session_id: str) -> Session:
        """获取会话，只加载活跃窗口"""
        session = Session(id=session_id)

        # 1. 加载活跃窗口（最近 N 条）
        cursor = self.db.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, self.active_window_size))

        session.messages = [self._row_to_message(row) for row in cursor.fetchall()]
        session.messages.reverse()  # 恢复时间顺序

        # 2. 加载摘要（如果有）
        cursor = self.db.execute("""
            SELECT summary FROM session_summaries
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))

        row = cursor.fetchone()
        if row:
            session.summary = row[0]

        return session

    async def add_message(self, session_id: str, message: Message):
        """添加消息，自动触发压缩"""
        # 写入消息
        self.db.execute("""
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, message.role, message.content, message.timestamp))

        # 检查是否需要生成摘要
        count = self._get_message_count(session_id)
        if count % self.summary_chunk_size == 0:
            await self._generate_summary(session_id)

        # 检查是否需要归档
        if count > self.archive_threshold:
            await self._archive_old_messages(session_id)

        self.db.commit()

    async def _generate_summary(self, session_id: str):
        """生成摘要（异步，不阻塞主流程）"""
        # 获取需要摘要的消息
        messages = await self._get_messages_for_summary(session_id)

        # 使用 LLM 生成摘要
        summary = await self._llm_summarize(messages)

        # 存储摘要
        self.db.execute("""
            INSERT INTO session_summaries (session_id, summary, message_range_start, message_range_end)
            VALUES (?, ?, ?, ?)
        """, (session_id, summary, messages[0].timestamp, messages[-1].timestamp))

    async def _archive_old_messages(self, session_id: str):
        """归档旧消息到压缩存储"""
        # 获取需要归档的消息
        cursor = self.db.execute("""
            SELECT id FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, self.archive_threshold // 2))

        ids_to_archive = [row[0] for row in cursor.fetchall()]

        if ids_to_archive:
            # 压缩并存储到归档表
            await self._compress_and_archive(session_id, ids_to_archive)

            # 从主表删除
            self.db.execute(f"""
                DELETE FROM messages WHERE id IN ({','.join('?' * len(ids_to_archive))})
            """, ids_to_archive)
```

**权衡**:
- ✅ 解决内存问题
- ✅ 支持超长会话
- ⚠️ 摘要可能丢失细节
- ⚠️ 归档消息访问延迟

---

### ADR-005: 成本控制设计

**问题**: 需要全局成本控制，防止 Token 消耗失控。

**决策**: 多层级成本控制体系。

```
┌─────────────────────────────────────────────────────────┐
│                    Cost Control                          │
│                                                          │
│  Level 1: 会话级限制                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ max_tokens_per_session: 1,000,000              │    │
│  │ max_tool_calls_per_session: 500                │    │
│  │ max_iterations_per_request: 20                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 2: 用户级限制                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ daily_token_limit: 10,000,000                  │    │
│  │ hourly_request_limit: 100                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 3: 全局限制                                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │ global_daily_budget: $100                       │    │
│  │ auto_throttle: true                             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 4: 自适应降级                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 当预算不足时：                                   │    │
│  │ - 切换到更便宜的模型                            │    │
│  │ - 减少上下文长度                                │    │
│  │ - 拒绝非关键请求                                │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**实现**:

```python
@dataclass
class CostConfig:
    """成本配置"""
    # 会话级
    max_tokens_per_session: int = 1_000_000
    max_tool_calls_per_session: int = 500
    max_iterations_per_request: int = 20

    # 用户级
    daily_token_limit: int = 10_000_000
    hourly_request_limit: int = 100

    # 全局
    global_daily_budget_usd: float = 100.0
    auto_throttle: bool = True

    # 自适应降级
    fallback_model: str = "claude-haiku-4-5"  # 便宜的模型
    context_reduction_ratio: float = 0.5      # 减少上下文比例


class CostController:
    """成本控制器"""

    def __init__(self, config: CostConfig, storage: "CostStorage"):
        self.config = config
        self.storage = storage

    async def check_session_budget(self, session_id: str) -> bool:
        """检查会话预算"""
        usage = await self.storage.get_session_usage(session_id)

        if usage.total_tokens >= self.config.max_tokens_per_session:
            raise BudgetExceededError(
                f"Session token limit reached: {usage.total_tokens}/{self.config.max_tokens_per_session}"
            )

        if usage.tool_calls >= self.config.max_tool_calls_per_session:
            raise BudgetExceededError("Session tool call limit reached")

        return True

    async def check_user_budget(self, user_id: str) -> bool:
        """检查用户预算"""
        daily_usage = await self.storage.get_daily_user_usage(user_id)

        if daily_usage.tokens >= self.config.daily_token_limit:
            raise BudgetExceededError("Daily token limit reached")

        hourly_requests = await self.storage.get_hourly_request_count(user_id)
        if hourly_requests >= self.config.hourly_request_limit:
            raise RateLimitError("Hourly request limit reached")

        return True

    async def check_global_budget(self) -> bool:
        """检查全局预算"""
        daily_cost = await self.storage.get_daily_cost()

        if daily_cost >= self.config.global_daily_budget_usd:
            if self.config.auto_throttle:
                # 触发自适应降级
                return False
            raise BudgetExceededError("Global daily budget exceeded")

        return True

    async def should_downgrade(self) -> tuple[bool, str]:
        """判断是否应该降级"""
        daily_cost = await self.storage.get_daily_cost()
        budget = self.config.global_daily_budget_usd

        if daily_cost >= budget * 0.8:  # 80% 预算
            return True, self.config.fallback_model

        return False, ""

    async def record_usage(
        self,
        session_id: str,
        user_id: str,
        usage: TokenUsage,
        cost_usd: float
    ):
        """记录使用量"""
        await self.storage.record(
            session_id=session_id,
            user_id=user_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now()
        )


class AdaptiveDegradation:
    """自适应降级"""

    def __init__(self, cost_controller: CostController, llm_registry: dict):
        self.cost = cost_controller
        self.llm_registry = llm_registry

    async def select_model(self, preferred_model: str) -> str:
        """选择合适的模型"""
        should_downgrade, fallback = await self.cost.should_downgrade()

        if should_downgrade:
            return fallback

        return preferred_model

    async def adjust_context_budget(
        self,
        requested_tokens: int
    ) -> int:
        """调整上下文预算"""
        should_downgrade, _ = await self.cost.should_downgrade()

        if should_downgrade:
            return int(requested_tokens * self.cost.config.context_reduction_ratio)

        return requested_tokens
```

**权衡**:
- ✅ 防止成本失控
- ✅ 支持多租户
- ⚠️ 降级可能影响体验
- ⚠️ 需要准确的价格表

---

### ADR-006: Skill 冲突解决

**问题**: 多个 Skill 同时激活可能导致指令冲突。

**决策**: 实现优先级 + 互斥 + 融合策略。

```python
@dataclass
class SkillPriority:
    """技能优先级"""
    skill_name: str
    priority: int = 0           # 数值越高优先级越高
    exclusive: bool = False     # 是否互斥（激活时禁用其他）
    conflicts_with: List[str] = field(default_factory=list)  # 冲突列表


class SkillConflictResolver:
    """技能冲突解决器"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.priorities: Dict[str, SkillPriority] = {}

    def set_priority(self, priority: SkillPriority):
        """设置技能优先级"""
        self.priorities[priority.skill_name] = priority

    def resolve(self, matched_skills: List[Skill], user_input: str) -> List[Skill]:
        """解决冲突，返回最终激活的技能"""

        if not matched_skills:
            return []

        # 1. 检查互斥技能
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)
            if priority and priority.exclusive:
                # 只保留这个互斥技能
                return [skill]

        # 2. 检查冲突对
        result = []
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)

            if priority:
                # 检查是否与已选技能冲突
                has_conflict = any(
                    s.name in priority.conflicts_with
                    for s in result
                )
                if has_conflict:
                    continue

            result.append(skill)

        # 3. 按优先级排序，保留前 N 个
        result.sort(
            key=lambda s: self.priorities.get(s.name, SkillPriority(s.name)).priority,
            reverse=True
        )

        # 最多激活 2 个技能
        return result[:2]

    def merge_prompts(
        self,
        system_prompt: str,
        skills: List[Skill]
    ) -> str:
        """融合多个技能的提示"""
        if not skills:
            return system_prompt

        if len(skills) == 1:
            return f"{system_prompt}\n\n# Active Skill: {skills[0].name}\n\n{skills[0].content}"

        # 多个技能时，按优先级组织
        skill_sections = []
        for i, skill in enumerate(skills, 1):
            skill_sections.append(f"## Skill {i}: {skill.name}\n\n{skill.content}")

        return f"{system_prompt}\n\n# Active Skills\n\n" + "\n\n".join(skill_sections)


# 使用示例
resolver = SkillConflictResolver(registry)

# 设置优先级
resolver.set_priority(SkillPriority(
    skill_name="code-review",
    priority=10,
    exclusive=False,
    conflicts_with=["debug"]  # code-review 和 debug 不兼容
))

resolver.set_priority(SkillPriority(
    skill_name="think",
    priority=100,
    exclusive=True  # think 激活时禁用其他技能
))

# 解决冲突
matched = registry.find_matching_skills("review and debug this code")
final_skills = resolver.resolve(matched, user_input)
```

**权衡**:
- ✅ 解决指令冲突
- ✅ 可配置优先级
- ⚠️ 需要用户配置（或学习）
- ⚠️ 可能遗漏一些技能

---

### ADR-007: 向量检索可选化

**问题**: 向量检索增加复杂度和成本，不一定必要。

**决策**: 向量检索作为可选插件，默认关闭。

```python
@dataclass
class MemoryConfig:
    """记忆配置"""
    storage_type: str = "file"

    # 向量检索（可选）
    enable_vector_search: bool = False  # 默认关闭
    embedding_model: str = "text-embedding-3-small"
    vector_db: str = "chroma"

    # 简单检索（默认）
    enable_keyword_search: bool = True  # 默认开启
```

**启用条件**:
- 会话数 > 1000
- 需要跨会话检索
- 有专门的向量数据库

---

## MVP 范围定义

基于上述分析，MVP 范围如下：

### ✅ MVP 必须有

| 功能 | 说明 |
|------|------|
| Agent Loop | 核心循环 + 并行工具 + 重试 |
| Tool System | 内置工具 + 权限控制 |
| Memory (基础) | File/SQLite 存储 + 滑动窗口 |
| Skills (基础) | 加载 + 激活 + 注入（无冲突解决） |
| 成本控制 | 会话级 Token 限制 |

### ⚠️ MVP 简化版

| 功能 | 简化方案 |
|------|----------|
| 上下文压缩 | 启发式摘要（不用 LLM） |
| 技能激活 | 最多 1 个（无冲突处理） |
| 触发器 | 只支持 Cron |

### ❌ MVP 不做

| 功能 | 延后原因 |
|------|----------|
| 向量检索 | 复杂度高，非核心 |
| 自动学习技能 | 实验性功能 |
| 多代理编排 | 需要先验证单代理 |
| 真正的沙箱 | 依赖外部工具（Docker） |

---

## 性能基准

### 目标指标

| 指标 | MVP 目标 | 生产目标 |
|------|----------|----------|
| 单次请求延迟 | < 5s | < 2s |
| 并发会话数 | 10 | 1000 |
| 会话最大消息数 | 100 | 10000 |
| 内存占用（空闲） | < 100MB | < 50MB |
| 内存占用（运行） | < 500MB | < 200MB |

### 测试场景

1. **短会话测试**: 10 条消息，验证基础流程
2. **长会话测试**: 1000 条消息，验证扩展性
3. **并发测试**: 100 并发请求，验证资源隔离
4. **成本测试**: 1000 次请求，验证成本追踪

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 长会话 OOM | 高 | 高 | 分片存储 + 滑动窗口 |
| 成本超支 | 中 | 高 | 多级预算控制 + 自动降级 |
| Skill 冲突 | 中 | 中 | 优先级 + 互斥机制 |
| 向量检索慢 | 低 | 低 | 默认关闭，按需启用 |
