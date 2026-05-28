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

---

## 内嵌 SDK 特有风险（架构评审反馈）

### ADR-008: 多进程/分布式环境状态管理

**问题**: 内嵌 SDK 在多进程环境（Gunicorn 多 Worker、K8s 多副本）下的状态灾难：
- SQLite 多进程并发写入导致 `database is locked`
- Trigger 在每个 Worker 进程中独立启动，导致重复触发
- Session 内存缓存不同步，Webhook 请求可能打到错误的 Worker

**决策**: 引入分布式状态后端 + 分布式锁 + 明确部署约束。

```python
from dataclasses import dataclass
from enum import Enum

class DeploymentMode(Enum):
    SINGLETON = "singleton"      # 单进程，使用 File/SQLite
    DISTRIBUTED = "distributed"  # 多进程，必须使用 Redis/PostgreSQL

@dataclass
class DistributedConfig:
    """分布式配置"""
    mode: DeploymentMode = DeploymentMode.SINGLETON
    
    # 分布式存储（当 mode=DISTRIBUTED 时必需）
    storage_backend: str = "redis"  # redis, postgresql
    storage_url: str = ""
    
    # 分布式锁
    lock_backend: str = "redis"
    lock_ttl_seconds: int = 30
    
    # Trigger 配置
    trigger_leader_election: bool = True  # 启用 Leader 选举，只有 Leader 执行 Trigger


class DistributedTriggerManager:
    """分布式触发器管理器"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        self._lock = None
        self._is_leader = False
        
    async def acquire_leader_lock(self) -> bool:
        """获取 Leader 锁（只有 Leader 执行 Trigger）"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True
            
        # 使用 Redis Redlock
        import redis.asyncio as redis
        client = redis.from_url(self.config.storage_url)
        
        self._lock = client.lock(
            "harness:trigger:leader",
            timeout=self.config.lock_ttl_seconds,
            blocking=False
        )
        
        try:
            self._is_leader = await self._lock.acquire()
            return self._is_leader
        except Exception:
            return False
    
    async def should_execute_trigger(self) -> bool:
        """判断当前实例是否应该执行 Trigger"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True
        return self._is_leader
```

**部署约束文档**:
```
## 部署模式

### 单进程模式（默认）
- 适用于：CLI 工具、脚本、单 Worker 应用
- 存储：File / SQLite
- Trigger：直接在进程内运行

### 多进程模式
- 适用于：FastAPI + Gunicorn、K8s 多副本
- 存储：必须使用 Redis / PostgreSQL
- Trigger：必须启用 Leader 选举，或独立部署 Trigger Worker

### 推荐架构
┌─────────────────────────────────────────────────────┐
│                    K8s Cluster                       │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ API Server  │  │ API Server  │  │ API Server  │ │
│  │ (Worker)    │  │ (Worker)    │  │ (Worker)    │ │
│  │ - 无 Trigger│  │ - 无 Trigger│  │ - 无 Trigger│ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │           Trigger Worker (单副本)            │   │
│  │           - Leader Election                  │   │
│  │           - 执行所有 Cron/Webhook            │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │                  Redis                        │   │
│  │           - Session Store                     │   │
│  │           - Distributed Lock                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**权衡**:
- ✅ 支持生产级部署
- ✅ 避免 Trigger 重复执行
- ⚠️ 增加运维复杂度（需要 Redis）
- ⚠️ 需要额外的 Trigger Worker 部署

---

### ADR-009: MCP 子进程生命周期管理

**问题**: `StdioTransport` 启动的 MCP 子进程在宿主崩溃时变成孤儿/僵尸进程。

**决策**: 实现严格的进程生命周期管理 + 健康检查。

```python
import os
import signal
import atexit
from contextlib import asynccontextmanager
from typing import Optional
import asyncio

class MCPProcessManager:
    """MCP 进程管理器"""
    
    def __init__(self):
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}
        self._setup_cleanup_hooks()
    
    def _setup_cleanup_hooks(self):
        """设置清理钩子"""
        # 正常退出时清理
        atexit.register(self._cleanup_all_sync)
        
        # SIGTERM/SIGINT 时清理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self._cleanup_all_sync()
        sys.exit(0)
    
    def _cleanup_all_sync(self):
        """同步清理所有进程"""
        for name, process in self._processes.items():
            try:
                if process.returncode is None:
                    # 发送 SIGTERM 给整个进程组
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
    
    async def start_process(
        self,
        name: str,
        command: str,
        args: list,
        env: dict
    ) -> asyncio.subprocess.Process:
        """启动进程（创建新进程组）"""
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **env},
            # 创建新进程组，便于批量终止
            start_new_session=True
        )
        
        self._processes[name] = process
        
        # 启动健康检查
        self._health_tasks[name] = asyncio.create_task(
            self._health_check(name, process)
        )
        
        return process
    
    async def _health_check(self, name: str, process: asyncio.subprocess.Process):
        """健康检查任务"""
        while process.returncode is None:
            try:
                # 每 30 秒检查一次
                await asyncio.sleep(30)
                
                # 可以发送 ping 消息检查 MCP 进程健康
                # ...
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 进程异常，尝试重启
                await self._restart_process(name)
                break
    
    async def stop_process(self, name: str):
        """停止指定进程"""
        if name in self._processes:
            process = self._processes[name]
            
            # 取消健康检查
            if name in self._health_tasks:
                self._health_tasks[name].cancel()
            
            # 优雅终止
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            finally:
                del self._processes[name]


@asynccontextmanager
async def mcp_session(name: str, command: str, args: list, env: dict):
    """MCP 会话上下文管理器"""
    manager = MCPProcessManager()
    process = await manager.start_process(name, command, args, env)
    
    try:
        yield process
    finally:
        await manager.stop_process(name)


# 使用示例
async def main():
    async with mcp_session(
        "filesystem",
        "mcp-server-filesystem",
        ["/workspace"],
        {}
    ) as process:
        # 使用 MCP 客户端通信
        pass
    # 退出时自动清理
```

**权衡**:
- ✅ 防止孤儿/僵尸进程
- ✅ 支持优雅关闭和自动重启
- ⚠️ 增加代码复杂度
- ⚠️ Windows 平台信号支持有限

---

### ADR-010: 沙箱执行的轻量化方案

**问题**: Docker 沙箱每次执行延迟高达数秒，且需要 Docker 权限，不适合高频工具调用。

**决策**: MVP 放弃 Docker，采用轻量级隔离 + 严格白名单。

```python
from dataclasses import dataclass
from typing import List, Set
import subprocess
import shutil

@dataclass
class LightweightSandboxConfig:
    """轻量级沙箱配置"""
    # 白名单命令
    allowed_commands: Set[str] = None
    
    # 禁止的命令模式
    blocked_patterns: List[str] = None
    
    # 资源限制
    max_execution_time: float = 30.0
    max_output_size: int = 1_000_000  # 1MB
    
    # 环境隔离
    allowed_env_vars: Set[str] = None
    blocked_env_vars: Set[str] = None

class LightweightSandbox:
    """轻量级沙箱执行器"""
    
    DEFAULT_BLOCKED_PATTERNS = [
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "mkfs",
        "dd if=",
        "> /dev/",
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  # Fork bomb
    ]
    
    def __init__(self, config: LightweightSandboxConfig = None):
        self.config = config or LightweightSandboxConfig()
        self.config.blocked_patterns = (
            self.config.blocked_patterns or self.DEFAULT_BLOCKED_PATTERNS
        )
    
    def validate_command(self, command: str) -> tuple[bool, str]:
        """验证命令安全性"""
        # 1. 检查黑名单
        for pattern in self.config.blocked_patterns:
            if pattern in command:
                return False, f"Blocked pattern: {pattern}"
        
        # 2. 白名单检查（如果配置了）
        if self.config.allowed_commands:
            cmd_base = command.split()[0] if command.split() else ""
            if shutil.which(cmd_base) not in self.config.allowed_commands:
                return False, f"Command not in whitelist: {cmd_base}"
        
        # 3. 危险路径检查
        dangerous_paths = ["/etc", "/root", "/home", "~/.ssh", "~/.aws"]
        for path in dangerous_paths:
            if path in command:
                return False, f"Dangerous path: {path}"
        
        return True, ""
    
    async def execute(
        self,
        command: str,
        cwd: str = None,
        env: dict = None,
        timeout: float = None
    ) -> "SandboxResult":
        """在沙箱中执行命令"""
        
        # 验证命令
        valid, reason = self.validate_command(command)
        if not valid:
            return SandboxResult(success=False, error=reason)
        
        # 构建隔离环境
        clean_env = self._build_clean_env(env)
        
        # 执行（使用 setrlimit 限制资源）
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=clean_env,
                # 资源限制
                preexec_fn=self._set_resource_limits
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.config.max_execution_time
            )
            
            # 输出大小限制
            stdout = stdout[:self.config.max_output_size]
            
            return SandboxResult(
                success=process.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=process.returncode
            )
            
        except asyncio.TimeoutError:
            process.kill()
            return SandboxResult(success=False, error="Timeout")
    
    def _build_clean_env(self, extra_env: dict = None) -> dict:
        """构建干净的环境变量"""
        # 只保留安全的环境变量
        safe_vars = {"PATH", "HOME", "USER", "LANG", "LC_ALL"}
        if self.config.allowed_env_vars:
            safe_vars.update(self.config.allowed_env_vars)
        
        env = {k: v for k, v in os.environ.items() if k in safe_vars}
        
        # 移除敏感变量
        sensitive = {
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN", "DATABASE_URL"
        }
        for var in sensitive:
            env.pop(var, None)
        
        if extra_env:
            env.update(extra_env)
        
        return env
    
    @staticmethod
    def _set_resource_limits():
        """设置进程资源限制"""
        import resource
        
        # 限制 CPU 时间（秒）
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        
        # 限制内存（字节）- 512MB
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        
        # 限制进程数
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
        
        # 禁止创建新文件
        # resource.setrlimit(resource.RLIMIT_NOFILE, (0, 0))
```

**权衡**:
- ✅ 毫秒级执行延迟
- ✅ 无需 Docker 权限
- ✅ 适用于云原生环境
- ⚠️ 隔离强度低于容器
- ⚠️ Windows 平台 `setrlimit` 不可用

---

### ADR-011: Skill 自学习的人机协作机制

**问题**: 自动生成的 Skill 质量不可控，可能污染 System Prompt 或引入安全漏洞。

**决策**: 自学习 Skill 必须进入 Draft 状态，经过人工审核后才能激活。

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime

class SkillStatus(Enum):
    DRAFT = "draft"        # 草稿，等待审核
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 已批准，可激活
    REJECTED = "rejected"  # 已拒绝

@dataclass
class DraftSkill:
    """草稿技能"""
    skill: Skill
    status: SkillStatus = SkillStatus.DRAFT
    created_at: datetime = None
    reviewed_at: datetime = None
    reviewed_by: str = ""
    rejection_reason: str = ""

class SkillReviewManager:
    """技能审核管理器"""
    
    def __init__(
        self,
        draft_dir: str = "~/.harness/skills/drafts",
        approved_dir: str = "~/.harness/skills/approved"
    ):
        self.draft_dir = Path(draft_dir).expanduser()
        self.approved_dir = Path(approved_dir).expanduser()
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
    
    async def submit_for_review(self, skill: Skill) -> str:
        """提交技能审核"""
        draft_id = f"draft_{skill.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存到草稿目录
        draft_path = self.draft_dir / f"{draft_id}.md"
        skill.to_file(draft_path)
        
        # 记录元数据
        meta = {
            "status": SkillStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "skill_name": skill.name
        }
        self._save_meta(draft_path, meta)
        
        return draft_id
    
    def list_pending(self) -> List[DraftSkill]:
        """列出待审核的技能"""
        pending = []
        for draft_file in self.draft_dir.glob("*.md"):
            meta = self._load_meta(draft_file)
            if meta.get("status") == SkillStatus.PENDING.value:
                skill = Skill.from_file(draft_file)
                pending.append(DraftSkill(
                    skill=skill,
                    status=SkillStatus.PENDING,
                    created_at=datetime.fromisoformat(meta.get("created_at"))
                ))
        return pending
    
    async def approve(self, draft_id: str, reviewer: str = "user") -> bool:
        """批准技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False
        
        # 移动到批准目录
        skill = Skill.from_file(draft_path)
        approved_path = self.approved_dir / f"{skill.name}.md"
        skill.to_file(approved_path)
        
        # 更新元数据
        meta = self._load_meta(draft_path)
        meta["status"] = SkillStatus.APPROVED.value
        meta["reviewed_at"] = datetime.now().isoformat()
        meta["reviewed_by"] = reviewer
        self._save_meta(draft_path, meta)
        
        # 删除草稿（或归档）
        draft_path.unlink()
        
        return True
    
    async def reject(self, draft_id: str, reason: str) -> bool:
        """拒绝技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False
        
        meta = self._load_meta(draft_path)
        meta["status"] = SkillStatus.REJECTED.value
        meta["reviewed_at"] = datetime.now().isoformat()
        meta["rejection_reason"] = reason
        self._save_meta(draft_path, meta)
        
        return True


# CLI 命令
# harness skill review --list          # 列出待审核
# harness skill approve <draft_id>      # 批准
# harness skill reject <draft_id> -r "不安全"  # 拒绝
```

**权衡**:
- ✅ 防止低质量 Skill 污染
- ✅ Human-in-the-loop 安全保障
- ⚠️ 增加维护成本
- ⚠️ 需要开发者主动参与审核

---

### ADR-012: 成本控制的熔断机制

**问题**: LLM 可能陷入死循环，消耗完预算后才停止。

**决策**: 增加熔断机制，检测异常模式并强制中断。

```python
from dataclasses import dataclass, field
from collections import deque
from typing import Deque
import time

@dataclass
class LoopPattern:
    """循环模式记录"""
    tool_name: str
    arguments_hash: str
    timestamp: float

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    # 相同工具调用次数阈值
    same_tool_threshold: int = 5
    
    # 时间窗口（秒）
    time_window: float = 60.0
    
    # 相似参数阈值（0-1）
    similarity_threshold: float = 0.8
    
    # 错误重试阈值
    error_threshold: int = 3
    
    # 冷却时间（秒）
    cooldown_seconds: float = 300.0

class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self._call_history: Deque[LoopPattern] = deque(maxlen=100)
        self._error_count = 0
        self._last_trip_time: float = 0
        self._tripped = False
    
    def record_call(self, tool_name: str, arguments: dict):
        """记录工具调用"""
        args_hash = self._hash_arguments(arguments)
        self._call_history.append(LoopPattern(
            tool_name=tool_name,
            arguments_hash=args_hash,
            timestamp=time.time()
        ))
        
        # 检查是否应该熔断
        if self._should_trip():
            self._trip()
    
    def record_error(self):
        """记录错误"""
        self._error_count += 1
        if self._error_count >= self.config.error_threshold:
            self._trip()
    
    def _should_trip(self) -> bool:
        """判断是否应该熔断"""
        if len(self._call_history) < self.config.same_tool_threshold:
            return False
        
        # 获取时间窗口内的调用
        now = time.time()
        recent = [
            p for p in self._call_history
            if now - p.timestamp < self.config.time_window
        ]
        
        if len(recent) < self.config.same_tool_threshold:
            return False
        
        # 检查相同工具的重复调用
        tool_counts = {}
        for pattern in recent:
            key = f"{pattern.tool_name}:{pattern.arguments_hash}"
            tool_counts[key] = tool_counts.get(key, 0) + 1
            
            if tool_counts[key] >= self.config.same_tool_threshold:
                return True
        
        return False
    
    def _trip(self):
        """触发熔断"""
        self._tripped = True
        self._last_trip_time = time.time()
    
    def is_open(self) -> bool:
        """熔断器是否打开（阻止执行）"""
        if not self._tripped:
            return False
        
        # 检查冷却时间
        if time.time() - self._last_trip_time > self.config.cooldown_seconds:
            self._reset()
            return False
        
        return True
    
    def _reset(self):
        """重置熔断器"""
        self._tripped = False
        self._error_count = 0
        self._call_history.clear()
    
    @staticmethod
    def _hash_arguments(arguments: dict) -> str:
        """计算参数哈希（用于相似性检测）"""
        import json
        import hashlib
        return hashlib.md5(
            json.dumps(arguments, sort_keys=True).encode()
        ).hexdigest()[:16]


class CircuitBreakerError(Exception):
    """熔断错误"""
    def __init__(self, message: str, stats: dict):
        super().__init__(message)
        self.stats = stats
```

**权衡**:
- ✅ 防止无限循环消耗预算
- ✅ 自动检测异常模式
- ⚠️ 可能误杀正常的长任务
- ⚠️ 需要调优阈值参数

---

## MVP 范围调整（基于架构评审）

### ✂️ MVP 延后/移除的功能

| 功能 | 原计划 | 调整 | 原因 |
|------|--------|------|------|
| 多代理编排 | Phase 3 | v2.0 | 掩盖底层 Bug，需先验证单代理 |
| Skill 自学习 | Phase 2 | 独立插件 `harness-ml` | 不可控行为，实验性功能 |
| Webhook Trigger | MVP | Phase 2 | 应由宿主应用处理，SDK 不绑定路由 |
| FileWatch Trigger | Phase 2 | Phase 3 | 非核心，复杂度高 |

### 🚀 MVP 必须强化的功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 流式输出背压处理 | P0 | 定义 AsyncGenerator 缓冲行为 |
| 中断与恢复 | P0 | 长任务优雅中断 + 状态持久化 |
| Mock 测试工具链 | P0 | pytest 插件，`@pytest.mark.harness_mock` |
| OpenTelemetry 集成 | P1 | 替代自研 LoopTracer |
| 增量 Token 计数 | P1 | 缓存历史 Token，避免重复计算 |

### 调整后的 MVP 范围

| 功能 | 说明 | 状态 |
|------|------|------|
| Agent Loop | 核心循环 + 并行工具 + 重试 + 熔断 | ✅ 必须 |
| Tool System | 内置工具 + 权限控制 + 轻量沙箱 | ✅ 必须 |
| Memory (基础) | File/SQLite + 滑动窗口 | ✅ 必须 |
| Skills (基础) | 加载 + 激活 + 注入（无自学习） | ✅ 必须 |
| 成本控制 | 会话级限制 + 熔断机制 | ✅ 必须 |
| Cron Trigger | 仅 Cron，单进程模式 | ✅ 必须 |
| Mock 测试 | pytest 集成 | ✅ 必须 |
| OpenTelemetry | Span 导出 | ⚠️ 推荐 |

---

## 生产级架构优化（第二轮评审反馈）

### ADR-013: SQLite 生产化配置

**问题**: 默认 SQLite 配置在高并发下会遭遇 `database is locked` 错误。

**决策**: 启用 WAL 模式 + 连接池 + 合理的超时配置。

```python
import aiosqlite
from contextlib import asynccontextmanager

class ProductionSQLiteStore:
    """生产级 SQLite 存储"""
    
    def __init__(
        self,
        db_path: str,
        pool_size: int = 5,
        timeout: float = 30.0
    ):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: list[aiosqlite.Connection] = []
        self._lock = asyncio.Lock()
    
    async def _init_connection(self, conn: aiosqlite.Connection):
        """初始化连接配置"""
        # 启用 WAL 模式（写并发关键）
        await conn.execute("PRAGMA journal_mode=WAL")
        
        # 同步模式设置
        await conn.execute("PRAGMA synchronous=NORMAL")
        
        # 增加 busy_timeout（毫秒）
        await conn.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)}")
        
        # 缓存大小（页数，负数表示 KB）
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB
        
        # 外键约束
        await conn.execute("PRAGMA foreign_keys=ON")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取连接（连接池模式）"""
        async with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = await aiosqlite.connect(self.db_path)
                await self._init_connection(conn)
        
        try:
            yield conn
        finally:
            async with self._lock:
                if len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    await conn.close()
    
    async def save(self, session: Session):
        """保存会话（带重试）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    # ... 保存逻辑
                    await conn.commit()
                return
            except aiosqlite.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                raise
```

**权衡**:
- ✅ 支持多 Worker 并发读取
- ✅ 写入不再轻易阻塞
- ⚠️ WAL 文件需要定期清理
- ⚠️ 高写入场景仍需 Redis/PostgreSQL

---

### ADR-014: Builder 模式重构 API

**问题**: `AgentHarness.__init__` 承担过多职责，配置项爆炸，难以测试和扩展。

**决策**: 采用 Builder 模式 + 组合模式，保持组件解耦。

```python
from typing import Optional, List, Union
from dataclasses import dataclass

@dataclass
class HarnessComponents:
    """Harness 组件容器"""
    llm: Optional[LLMClient] = None
    memory: Optional[SessionStore] = None
    tools: Optional[ToolRegistry] = None
    skills: Optional[SkillRegistry] = None
    triggers: Optional[TriggerManager] = None
    security: Optional[SecurityManager] = None
    observability: Optional[ObservabilityManager] = None


class HarnessBuilder:
    """Harness 构建器"""
    
    def __init__(self):
        self._components = HarnessComponents()
        self._config = {}
    
    def with_llm(
        self,
        model: str,
        api_key: str = None,
        provider: str = "anthropic",
        **kwargs
    ) -> "HarnessBuilder":
        """配置 LLM"""
        if provider == "anthropic":
            self._components.llm = AnthropicClient(
                api_key=api_key,
                model=model,
                **kwargs
            )
        elif provider == "openai":
            self._components.llm = OpenAIClient(
                api_key=api_key,
                model=model,
                **kwargs
            )
        return self
    
    def with_llm_client(self, client: LLMClient) -> "HarnessBuilder":
        """使用自定义 LLM 客户端"""
        self._components.llm = client
        return self
    
    def with_memory(
        self,
        store: Union[str, SessionStore],
        **kwargs
    ) -> "HarnessBuilder":
        """配置记忆存储"""
        if isinstance(store, str):
            if store == "file":
                self._components.memory = FileSessionStore(**kwargs)
            elif store == "sqlite":
                self._components.memory = ProductionSQLiteStore(**kwargs)
            elif store == "redis":
                self._components.memory = RedisSessionStore(**kwargs)
            elif store == "postgres":
                self._components.memory = PostgreSQLSessionStore(**kwargs)
        else:
            self._components.memory = store
        return self
    
    def with_tools(
        self,
        tools: List[Tool],
        permissions: PermissionSet = None
    ) -> "HarnessBuilder":
        """配置工具集"""
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)
        self._components.tools = registry
        return self
    
    def with_security(
        self,
        mode: str = "sandbox",
        **kwargs
    ) -> "HarnessBuilder":
        """配置安全策略"""
        if mode == "sandbox":
            self._components.security = SecurityManager(
                permissions=PermissionSet.sandbox(**kwargs)
            )
        elif mode == "readonly":
            self._components.security = SecurityManager(
                permissions=PermissionSet.read_only(**kwargs)
            )
        elif mode == "full":
            self._components.security = SecurityManager(
                permissions=PermissionSet.full_access()
            )
        return self
    
    def with_observability(
        self,
        backend: str = "opentelemetry",
        **kwargs
    ) -> "HarnessBuilder":
        """配置可观测性"""
        self._components.observability = ObservabilityManager(
            backend=backend,
            **kwargs
        )
        return self
    
    def with_skills(self, skill_dirs: List[str]) -> "HarnessBuilder":
        """配置技能目录"""
        registry = SkillRegistry()
        for dir_path in skill_dirs:
            registry.add_skill_dir(Path(dir_path))
        self._components.skills = registry
        return self
    
    def build(self) -> "AgentHarness":
        """构建 Harness 实例"""
        # 验证必需组件
        if not self._components.llm:
            raise ValueError("LLM client is required")
        
        # 使用默认值填充缺失组件
        if not self._components.memory:
            self._components.memory = FileSessionStore()
        
        if not self._components.tools:
            self._components.tools = ToolRegistry()
            self._components.tools.register_defaults()
        
        if not self._components.skills:
            self._components.skills = SkillRegistry()
        
        if not self._components.security:
            self._components.security = SecurityManager(
                permissions=PermissionSet.sandbox()
            )
        
        if not self._components.observability:
            self._components.observability = ObservabilityManager(
                backend="opentelemetry"
            )
        
        return AgentHarness(components=self._components)


# 使用示例
agent = (HarnessBuilder()
    .with_llm("claude-sonnet-4-6", api_key=os.environ["ANTHROPIC_API_KEY"])
    .with_memory("sqlite", db_path="~/.harness/harness.db")
    .with_tools([ReadTool(), BashTool(), GrepTool()])
    .with_security("sandbox", workspace="/workspace")
    .with_observability("opentelemetry", service_name="my-agent")
    .with_skills(["./skills", "~/.harness/skills"])
    .build()
)
```

**权衡**:
- ✅ 配置清晰，按需组装
- ✅ 组件可替换，易于测试
- ✅ IDE 自动补全友好
- ⚠️ 学习成本略高于单构造函数

---

### ADR-015: 流式中断与恢复机制

**问题**: `interrupt()` 无法中断正在进行的 LLM HTTP 请求或长耗时工具执行。

**决策**: 实现网络级中断 + 状态快照恢复。

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import asyncio

@dataclass
class LoopSnapshot:
    """循环快照（用于恢复）"""
    session_id: str
    messages: List[Message]
    current_iteration: int
    pending_tool_calls: List[ToolCall] = field(default_factory=list)
    last_llm_response: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class InterruptibleAgentLoop:
    """可中断的 Agent 循环"""
    
    def __init__(self, agent: "AgentHarness"):
        self.agent = agent
        self._current_task: Optional[asyncio.Task] = None
        self._snapshot: Optional[LoopSnapshot] = None
        self._http_client: Optional[aiohttp.ClientSession] = None
    
    async def run(
        self,
        prompt: str,
        session_id: str,
        checkpoint_interval: int = 1  # 每隔 N 次迭代保存快照
    ) -> "LoopResult":
        """可中断执行"""
        self._current_task = asyncio.current_task()
        iteration = 0
        
        try:
            while True:
                # 保存快照
                if iteration % checkpoint_interval == 0:
                    self._save_snapshot(session_id, iteration)
                
                # 执行一步（使用 shield 保护关键操作）
                result = await self._run_step(prompt, session_id, iteration)
                
                if result.finished:
                    return result
                
                iteration += 1
                
        except asyncio.CancelledError:
            # 保存中断点快照
            await self._save_interrupt_point(session_id, iteration)
            raise
    
    async def _run_step(self, prompt, session_id, iteration):
        """执行单步（可被取消）"""
        # 构建上下文（可取消）
        context = await asyncio.create_task(
            self.agent.context_builder.build(...)
        )
        
        try:
            # LLM 调用（可取消的网络请求）
            response = await self._call_llm_with_cancel(context)
            
            if response.tool_calls:
                # 工具执行（带超时）
                results = await asyncio.wait_for(
                    self._execute_tools(response.tool_calls),
                    timeout=self.agent.config.tool_timeout
                )
                # ... 继续循环
            
            return LoopResult(finished=True, ...)
            
        except asyncio.CancelledError:
            # 记录中断位置
            self._snapshot = LoopSnapshot(
                session_id=session_id,
                messages=context.messages,
                current_iteration=iteration
            )
            raise
    
    async def _call_llm_with_cancel(self, context):
        """可取消的 LLM 调用"""
        async with aiohttp.ClientSession() as session:
            # 使用 ClientSession 确保取消时正确关闭连接
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=...,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                return await response.json()
    
    async def _save_snapshot(self, session_id: str, iteration: int):
        """保存快照到记忆系统"""
        snapshot = LoopSnapshot(
            session_id=session_id,
            messages=await self.agent.memory.get_messages(session_id),
            current_iteration=iteration
        )
        await self.agent.memory.store_checkpoint(session_id, snapshot)
    
    async def interrupt(self):
        """中断当前执行"""
        if self._current_task:
            self._current_task.cancel()
    
    async def resume(self, session_id: str) -> "LoopResult":
        """从快照恢复执行"""
        snapshot = await self.agent.memory.load_checkpoint(session_id)
        if not snapshot:
            raise ValueError(f"No checkpoint found for session {session_id}")
        
        # 恢复状态
        self._snapshot = snapshot
        
        # 从中断点继续
        return await self.run(
            prompt="",
            session_id=session_id,
            start_iteration=snapshot.current_iteration
        )
```

**权衡**:
- ✅ 支持真正的网络级中断
- ✅ 可从中断点恢复，避免重复工具调用
- ⚠️ 增加快照存储成本
- ⚠️ 恢复逻辑需要处理状态一致性

---

### ADR-016: 输出过滤 (DLP)

**问题**: 工具执行结果可能包含敏感信息（API Key、密码、PII），直接返回给 LLM 会导致泄露。

**决策**: 在 `ToolExecutor` 返回前增加 `ResultSanitizer` 管道。

```python
import re
from dataclasses import dataclass
from typing import List, Callable, Pattern

@dataclass
class SanitizationRule:
    """脱敏规则"""
    name: str
    pattern: Pattern
    replacement: str
    description: str = ""


class ResultSanitizer:
    """结果脱敏器"""
    
    DEFAULT_RULES = [
        SanitizationRule(
            name="api_key",
            pattern=re.compile(r'(api[_-]?key["\s:=]+)["\']?[\w-]{20,}["\']?', re.I),
            replacement=r'\1[REDACTED]',
            description="API Key"
        ),
        SanitizationRule(
            name="password",
            pattern=re.compile(r'(password["\s:=]+)["\']?[^\s"\']{8,}["\']?', re.I),
            replacement=r'\1[REDACTED]',
            description="密码"
        ),
        SanitizationRule(
            name="secret_token",
            pattern=re.compile(r'(token["\s:=]+)["\']?[\w-]{20,}["\']?', re.I),
            replacement=r'\1[REDACTED]',
            description="Token"
        ),
        SanitizationRule(
            name="aws_key",
            pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
            replacement='AKIA[REDACTED]',
            description="AWS Access Key"
        ),
        SanitizationRule(
            name="email",
            pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            replacement='[EMAIL REDACTED]',
            description="邮箱地址"
        ),
        SanitizationRule(
            name="credit_card",
            pattern=re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
            replacement='[CARD REDACTED]',
            description="信用卡号"
        ),
        SanitizationRule(
            name="private_key",
            pattern=re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'),
            replacement='-----BEGIN PRIVATE KEY [REDACTED]-----',
            description="私钥"
        ),
    ]
    
    def __init__(
        self,
        rules: List[SanitizationRule] = None,
        max_length: int = 100_000,  # 最大输出长度
        custom_patterns: List[Pattern] = None
    ):
        self.rules = rules or self.DEFAULT_RULES
        self.max_length = max_length
        self.custom_patterns = custom_patterns or []
    
    def sanitize(self, content: str) -> str:
        """执行脱敏"""
        result = content
        
        # 1. 应用脱敏规则
        for rule in self.rules:
            result = rule.pattern.sub(rule.replacement, result)
        
        # 2. 应用自定义模式
        for pattern in self.custom_patterns:
            result = pattern.sub('[REDACTED]', result)
        
        # 3. 长度限制
        if len(result) > self.max_length:
            # 保留前后部分，中间用摘要替代
            head = result[:self.max_length // 2]
            tail = result[-self.max_length // 4:]
            result = f"{head}\n\n... [内容过长，已截断，原始长度: {len(content)}] ...\n\n{tail}"
        
        return result
    
    def get_redaction_report(self, original: str, sanitized: str) -> dict:
        """获取脱敏报告"""
        report = {
            "original_length": len(original),
            "sanitized_length": len(sanitized),
            "redactions": []
        }
        
        for rule in self.rules:
            matches = rule.pattern.findall(original)
            if matches:
                report["redactions"].append({
                    "rule": rule.name,
                    "description": rule.description,
                    "count": len(matches) if isinstance(matches, list) else 1
                })
        
        return report


class SanitizingToolExecutor(ToolExecutor):
    """带脱敏的工具执行器"""
    
    def __init__(
        self,
        registry: ToolRegistry,
        sanitizer: ResultSanitizer = None
    ):
        super().__init__(registry)
        self.sanitizer = sanitizer or ResultSanitizer()
    
    async def execute(
        self,
        call: ToolCall,
        context: ToolContext
    ) -> ToolResult:
        """执行工具并对结果脱敏"""
        result = await super().execute(call, context)
        
        if result.success and result.content:
            # 执行脱敏
            result.content = self.sanitizer.sanitize(result.content)
            
            # 记录脱敏报告（审计）
            if context.logger:
                report = self.sanitizer.get_redaction_report(
                    result.content,  # 已经脱敏了
                    result.content
                )
                if report["redactions"]:
                    context.logger.info(f"Sanitization applied: {report}")
        
        return result
```

**权衡**:
- ✅ 防止敏感信息泄露
- ✅ 可审计的脱敏记录
- ⚠️ 正则匹配可能有误报
- ⚠️ 无法处理所有场景（如编码绕过）

---

### ADR-017: OpenTelemetry 原生集成

**问题**: 自研 `LoopTracer` 无法与主流观测平台集成。

**决策**: 原生集成 OpenTelemetry，导出标准 Span。

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# 初始化 OTel
resource = Resource.create({"service.name": "harness-agent"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("harness.agent")


class ObservableAgentLoop:
    """可观测的 Agent 循环"""
    
    async def run(self, prompt: str, session_id: str) -> LoopResult:
        """执行循环（带 OTel 埋点）"""
        with tracer.start_as_current_span(
            "agent_loop.run",
            attributes={
                "session.id": session_id,
                "prompt.length": len(prompt)
            }
        ) as span:
            
            # 1. 构建上下文
            with tracer.start_as_current_span("context.build") as ctx_span:
                context = await self._build_context(session_id)
                ctx_span.set_attribute("context.token_count", context.token_count)
                ctx_span.set_attribute("context.message_count", len(context.messages))
            
            # 2. LLM 调用
            with tracer.start_as_current_span("llm.call") as llm_span:
                llm_span.set_attribute("llm.model", self.llm.model)
                llm_span.set_attribute("llm.max_tokens", self.llm.max_tokens)
                
                response = await self.llm.call(context)
                
                llm_span.set_attribute("llm.input_tokens", response.usage.input_tokens)
                llm_span.set_attribute("llm.output_tokens", response.usage.output_tokens)
                llm_span.set_attribute("llm.cache_read_tokens", response.usage.cache_read_tokens)
                llm_span.set_attribute("llm.stop_reason", response.stop_reason.value)
            
            # 3. 工具执行
            if response.tool_calls:
                with tracer.start_as_current_span("tools.execute") as tools_span:
                    tools_span.set_attribute("tools.count", len(response.tool_calls))
                    tools_span.set_attribute("tools.names", [tc.name for tc in response.tool_calls])
                    
                    results = await self._execute_tools(response.tool_calls)
                    
                    for i, result in enumerate(results):
                        tools_span.set_attribute(
                            f"tools.{response.tool_calls[i].name}.success",
                            result.success
                        )
            
            # 4. 记录最终指标
            span.set_attribute("loop.iterations", iteration)
            span.set_attribute("loop.total_tokens", total_tokens)
            span.set_status(Status(StatusCode.OK))
            
            return result
```

**导出的 Span 结构**:
```
agent_loop.run (session_id=xxx, prompt.length=100)
├── context.build (token_count=5000, message_count=10)
├── llm.call (model=claude-sonnet-4-6, input_tokens=5000, output_tokens=500)
│   ├── llm.call (第二次迭代)
│   └── ...
├── tools.execute (count=2, names=["read", "grep"])
│   ├── tools.read (success=true, duration=0.1s)
│   └── tools.grep (success=true, duration=0.2s)
└── memory.save (success=true)
```

**权衡**:
- ✅ 兼容 Langfuse、Datadog、Jaeger 等
- ✅ 标准化指标和追踪
- ⚠️ 引入额外依赖
- ⚠️ 需要配置 OTLP 收集端点

---

### ADR-018: 增量 Token 计数

**问题**: 每次循环都重新计算所有消息的 Token，`tiktoken` 阻塞事件循环。

**决策**: 增量计数 + 线程池执行 + 缓存。

```python
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, Optional
import functools

@dataclass
class CachedTokenCount:
    """缓存的 Token 计数"""
    message_id: str
    token_count: int
    content_hash: str
    computed_at: datetime


class IncrementalTokenCounter:
    """增量 Token 计数器"""
    
    def __init__(
        self,
        model: str,
        cache_size: int = 10000,
        approximate_threshold: int = 50000  # 超过此长度使用近似估算
    ):
        self.model = model
        self.cache_size = cache_size
        self.approximate_threshold = approximate_threshold
        
        # 缓存
        self._cache: Dict[str, CachedTokenCount] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Token 编码器（延迟加载）
        self._encoder = None
    
    @functools.lru_cache(maxsize=1000)
    def _get_encoder(self):
        """获取编码器（缓存）"""
        import tiktoken
        return tiktoken.encoding_for_model(self.model)
    
    async def count_message(self, message: Message) -> int:
        """计算单条消息的 Token 数"""
        # 检查缓存
        content_hash = self._hash_content(message.content)
        cache_key = f"{message.role}:{content_hash}"
        
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key].token_count
        
        self._cache_misses += 1
        
        # 在线程池中计算
        loop = asyncio.get_event_loop()
        token_count = await loop.run_in_executor(
            self._executor,
            self._count_sync,
            message.content
        )
        
        # 加上消息格式开销
        token_count += 4  # role + 格式开销
        
        # 缓存结果
        self._cache[cache_key] = CachedTokenCount(
            message_id=cache_key,
            token_count=token_count,
            content_hash=content_hash,
            computed_at=datetime.now()
        )
        
        return token_count
    
    def _count_sync(self, content: str) -> int:
        """同步计算（在线程池中执行）"""
        if len(content) > self.approximate_threshold:
            # 大文本使用近似估算
            return self._approximate_count(content)
        
        encoder = self._get_encoder()
        return len(encoder.encode(content))
    
    def _approximate_count(self, content: str) -> int:
        """近似估算（快速但不够精确）"""
        # 简单估算：字符数 / 4
        # 可以根据模型调整
        return len(content) // 4
    
    async def count_messages(self, messages: List[Message]) -> int:
        """计算多条消息的 Token 数（并行）"""
        tasks = [self.count_message(msg) for msg in messages]
        counts = await asyncio.gather(*tasks)
        return sum(counts)
    
    def _hash_content(self, content: str) -> str:
        """计算内容哈希"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache)
        }
```

**权衡**:
- ✅ 避免阻塞事件循环
- ✅ 缓存减少重复计算
- ⚠️ 近似估算不精确
- ⚠️ 内存占用增加

---

## 部署指南

### 支持的部署拓扑

| 拓扑 | 存储后端 | Trigger 模式 | 状态 |
|------|----------|--------------|------|
| 单进程脚本 | File/SQLite | 进程内 | ✅ MVP 支持 |
| FastAPI + 单 Worker | File/SQLite | 进程内 | ✅ MVP 支持 |
| FastAPI + Gunicorn (多 Worker) | Redis/PostgreSQL | Leader 选举 | ⚠️ Phase 2 |
| K8s 多副本 | Redis/PostgreSQL | 独立 Trigger Worker | ⚠️ Phase 2 |
| Celery Worker | Redis | Celery Beat | ⚠️ Phase 2 |

### 已知限制

1. **单进程模式**: SQLite 适合低并发，高并发需切换 WAL 模式
2. **多进程模式**: 必须使用 Redis/PostgreSQL，且 Trigger 需要 Leader 选举
3. **热重载**: 开发环境热重载会丢失内存状态，需要持久化存储
4. **Windows**: 部分信号处理和沙箱功能受限

---

## API 稳定性分类

### Public API (稳定，向后兼容)

```python
# 核心接口
AgentHarness.run(prompt, session_id)
AgentHarness.stream(prompt, session_id)
AgentHarness.interrupt()

# 工具注册
AgentHarness.register_tool(tool)
@agent.tool()

# 技能管理
AgentHarness.load_skill(path)
AgentHarness.activate_skill(name)

# 记忆
AgentHarness.remember(content, type)
AgentHarness.recall(query)
```

### Beta API (可能变更)

```python
# 触发器
AgentHarness.on_schedule(cron, prompt)
AgentHarness.on_webhook(endpoint, prompt)

# 中断恢复
AgentHarness.resume(session_id)

# 可观测性
AgentHarness.get_traces()
```

### Internal API (不保证兼容)

```python
# 内部组件
AgentHarness._loop
AgentHarness._components
ContextBuilder._compress_context()
```
