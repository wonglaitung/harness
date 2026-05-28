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
