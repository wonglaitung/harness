# 04 - 记忆系统详解

## 概述

记忆系统解决 LLM 无状态问题，提供跨会话的持久化和上下文管理。Harness 的记忆系统包含四层记忆架构、MEMORY.md 标准格式、向量检索和动态系统提示组装。

## 四层记忆架构

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Working Memory（工作记忆）              │
│ - 当前会话消息列表                               │
│ - 当前任务状态                                   │
│ - 临时变量和上下文                               │
├─────────────────────────────────────────────────┤
│ Layer 2: Session Memory（会话记忆）              │
│ - 会话摘要                                       │
│ - 关键决策记录                                   │
│ - 用户偏好                                       │
├─────────────────────────────────────────────────┤
│ Layer 3: Long-term Memory（长期记忆）            │
│ - MEMORY.md 持久记忆文件                         │
│ - 技能和模式                                     │
│ - 项目知识                                       │
│ - 历史经验                                       │
├─────────────────────────────────────────────────┤
│ Layer 4: Retrieved Memory（检索记忆）            │
│ - 向量语义搜索                                   │
│ - 历史对话检索                                   │
│ - 技能/文档检索                                  │
│ - 按需加载                                       │
└─────────────────────────────────────────────────┘
```


## MEMORY.md 标准

MEMORY.md 是 Harness 的持久记忆文件格式，用于跨会话保存重要信息。它采用分章节的 Markdown 格式，便于人工阅读和编辑。

### 文件格式

```markdown
# MEMORY.md

## User Profile
- Role: Software Developer
- Preferred Language: Python

## Key Decisions
- 2024-01-15: Chose SQLite for session storage due to its simplicity and performance
- 2024-01-16: Use qasync for PyQt integration instead of QThread

## Learned Patterns
- User prefers detailed explanations with code examples
- Avoid mocking database in integration tests

## Project Context
- This project uses Python 3.11+ with async/await patterns
- Code style follows Black formatting with 88 character line length
```

### 记忆类别

Harness 定义了四种记忆类别，每种对应一个专门的章节：

| 类别 | 章节标题 | 说明 | 示例 |
|------|----------|------|------|
| `USER_PROFILE` | User Profile | 用户角色、偏好、技能 | 用户是后端工程师，偏好 Python |
| `KEY_DECISIONS` | Key Decisions | 重要技术决策，带时间戳 | 2024-01-15: 选择 SQLite 作为会话存储 |
| `LEARNED_PATTERNS` | Learned Patterns | Agent 学习到的用户模式 | 用户喜欢详细的代码示例 |
| `PROJECT_CONTEXT` | Project Context | 项目特定约定和配置 | 代码遵循 Black 格式化，行宽 88 字符 |



### 核心类型

```python
from harness.memory.memory_file import MemoryEntry, MemoryCategory, MemorySource, MemorySections, MemoryFileManager
from pathlib import Path
from datetime import datetime

# MemoryEntry - 单个记忆条目
entry = MemoryEntry(
    category=MemoryCategory.KEY_DECISIONS,
    content="Chose SQLite for session storage",
    source=MemorySource.AGENT_OBSERVATION,
    created_at=datetime.now(),  # 自动设置创建时间
    metadata={"session_id": "abc123"},  # 可选元数据
)

# MemorySections - 所有记忆章节
sections = MemorySections(
    user_profile=["Role: Software Developer", "Preferred Language: Python"],
    key_decisions=["2024-01-15: Chose SQLite for session storage"],
    learned_patterns=["User prefers detailed explanations"],
    project_context=["Project uses Python 3.11+"],
)

# MemoryFileManager - 管理 MEMORY.md 文件
manager = MemoryFileManager(project_root=Path.cwd())
```

### 使用方式

```python
from harness.memory.memory_file import MemoryFileManager, MemoryEntry, MemoryCategory, MemorySource
from pathlib import Path

# 初始化管理器
manager = MemoryFileManager(project_root=Path("/path/to/project"))

# 检查是否存在 MEMORY.md
if manager.exists():
    # 加载现有记忆
    sections = manager.load()
    
    # 访问特定章节
    for pattern in sections.learned_patterns:
        print(f"学习到的模式: {pattern}")
else:
    # 创建默认记忆文件
    from harness.memory.memory_file import create_default_memory
    create_default_memory(Path("/path/to/project"))

# 添加新条目
new_entry = MemoryEntry(
    category=MemoryCategory.KEY_DECISIONS,
    content="Use qasync for PyQt integration",
    source=MemorySource.AGENT_OBSERVATION,
    created_at=datetime.now(),
    metadata={"source": "agent_observation"},
)
manager.add_entry(new_entry)

# 获取所有条目
key_decisions = manager.get_entries(MemoryCategory.KEY_DECISIONS)
for i, decision in enumerate(key_decisions):
    print(f"决策 {i}: {decision}")

# 格式化为 LLM 上下文字符串
context_string = manager.to_context_string()
print(f"上下文长度: {len(context_string)} 字符")

# 删除条目
manager.remove_entry(MemoryCategory.KEY_DECISIONS, 0)

# 清空所有记忆
manager.clear()
```

## VectorMemoryStore（向量检索）

向量检索提供语义搜索能力，可以搜索历史对话、技能和文档。这是一个可选功能，需要安装额外依赖：`pip install harness-ai[vector]`。

### 核心协议

```python
from harness.memory.vector_store import EmbeddingModel, VectorStore, VectorSearchResult

# EmbeddingModel 协议
class EmbeddingModel(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本嵌入向量"""
    
    @property
    def dimension(self) -> int:
        """返回嵌入维度"""

# VectorStore 协议
class VectorStore(Protocol):
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """添加向量到存储"""
    
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """搜索相似向量"""
    
    async def delete(self, ids: list[str]) -> None:
        """按ID删除向量"""
    
    async def clear(self) -> None:
        """清空所有向量"""
```

### VectorMemoryConfig

```python
from harness.memory.vector_store import VectorMemoryConfig

@dataclass
class VectorMemoryConfig:
    embedding_model: str = "mock"  # "mock", "openai", "sentence-transformers"
    persist_dir: Path | None = None  # 持久化目录
    collection_name: str = "harness_memory"  # 集合名称
    embedding_dimension: int = 384  # 嵌入维度
```

### VectorSearchResult

```python
@dataclass
class VectorSearchResult:
    id: str                    # 文档唯一标识符
    content: str               # 匹配内容
    score: float               # 相似度分数 (0-1)
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
```

### VectorMemoryStore 类

```python
from harness.memory.vector_store import VectorMemoryStore, VectorMemoryConfig

class VectorMemoryStore:
    def __init__(
        self,
        config: VectorMemoryConfig | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ):
        """初始化向量记忆存储
        
        Args:
            config: 配置对象
            embedding_model: 自定义嵌入模型（覆盖配置）
            vector_store: 自定义向量存储（覆盖配置）
        """
    
    async def add(
        self,
        id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加单个文档到存储"""
    
    async def add_batch(
        self,
        ids: list[str],
        contents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """批量添加文档到存储"""
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """语义搜索文档"""
    
    async def delete(self, ids: list[str]) -> None:
        """删除文档"""
    
    async def clear(self) -> None:
        """清空所有文档"""
    
    async def add_conversation(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """添加对话消息到存储"""
    
    async def search_conversations(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        """搜索对话历史"""
    
    async def add_skill(
        self,
        skill_name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加技能内容到存储"""
    
    async def search_skills(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """按语义相似度搜索技能"""
```

### 使用场景

```python
from harness.memory.vector_store import VectorMemoryStore, VectorMemoryConfig
from pathlib import Path

# 创建配置
config = VectorMemoryConfig(
    embedding_model="mock",  # 使用模拟嵌入模型（测试用）
    # embedding_model="openai",  # 使用 OpenAI 嵌入模型
    # embedding_model="sentence-transformers",  # 使用 sentence-transformers
)

# 创建向量存储
store = VectorMemoryStore(config)

# 添加文档
await store.add(
    id="doc1",
    content="用户偏好使用 PostgreSQL 而非 MySQL",
    metadata={"session_id": "abc123", "type": "preference"},
)

# 批量添加文档
await store.add_batch(
    ids=["doc2", "doc3", "doc4"],
    contents=[
        "项目使用 Python 3.11 和 async/await 模式",
        "代码风格遵循 Black 格式化，行宽 88 字符",
        "测试使用 pytest 框架，避免 mock 数据库",
    ],
    metadatas=[
        {"type": "project_context"},
        {"type": "coding_standard"},
        {"type": "testing"},
    ],
)

# 语义搜索
results = await store.search("数据库选择", top_k=3)
for result in results:
    print(f"[{result.score:.3f}] {result.content}")
    print(f"  元数据: {result.metadata}")

# 添加对话历史
messages = [
    {"role": "user", "content": "如何设置 Python 异步编程？"},
    {"role": "assistant", "content": "使用 asyncio 库和 async/await 语法。"},
]
await store.add_conversation("session_123", messages)

# 搜索对话历史
conversation_results = await store.search_conversations("异步编程", session_id="session_123")
for result in conversation_results:
    print(f"对话匹配: {result.content}")

# 添加技能
await store.add_skill(
    skill_name="code_review",
    content="代码审查时检查错误处理、类型注解和测试覆盖率。",
    metadata={"category": "development"},
)

# 搜索技能
skill_results = await store.search_skills("代码审查", top_k=2)
for result in skill_results:
    print(f"技能匹配: {result.content}")

# 删除文档
await store.delete(["doc1"])

# 清空存储
await store.clear()
```

## SystemPromptBuilder（动态系统提示组装）

SystemPromptBuilder 负责动态组装系统提示，将多个来源的内容合并为最终系统提示。

### SystemPromptSource

```python
from harness.memory.system_prompt import SystemPromptSource

@dataclass
class SystemPromptSource:
    name: str
    priority: int  # 优先级越高，在最终提示中越靠前
    content: str | Callable[[], str] | None = None
    file_path: Path | None = None
    required: bool = False  # 如果为 True，文件不存在时抛出错误
```

### SystemPromptConfig

```python
from harness.memory.system_prompt import SystemPromptConfig, SystemPromptBuilder

@dataclass
class SystemPromptConfig:
    base_prompt: str = ""  # 基础系统提示
    agents_md_path: Path | None = None  # AGENTS.md 文件路径
    memory_md_path: Path | None = None  # MEMORY.md 文件路径
    project_root: Path | None = None  # 项目根目录
    auto_discover: bool = True  # 自动发现 AGENTS.md 和 MEMORY.md
    custom_sources: dict[str, SystemPromptSource] = field(default_factory=dict)  # 自定义源
    section_separator: str = "\n\n---\n\n"  # 片段分隔符
```

### SystemPromptBuilder

```python
class SystemPromptBuilder:
    def __init__(self, config: SystemPromptConfig | None = None):
        """初始化系统提示构建器"""
        self.config = config or SystemPromptConfig()
        self._sources: list[SystemPromptSource] = []
        self._setup_default_sources()

    def add_source(self, source: SystemPromptSource) -> None:
        """添加新的提示源"""

    def remove_source(self, name: str) -> bool:
        """通过名称移除提示源，返回是否找到并移除"""

    def build(self) -> str:
        """构建最终系统提示"""

    def get_available_sources(self) -> list[str]:
        """获取有内容的源名称列表"""

    def get_source_content(self, name: str) -> str | None:
        """获取特定源的内容"""
```

### 组装优先级

```
1. 安全规则（最高优先级）
2. 角色定义
3. AGENTS.md 内容
4. 技能指令
5. 记忆上下文
6. 用户偏好
7. 基础提示（最低优先级）
```

### 使用方式

```python
from harness.memory.system_prompt import SystemPromptConfig, SystemPromptBuilder, SystemPromptSource
from pathlib import Path

# 创建配置
config = SystemPromptConfig(
    base_prompt="You are a helpful assistant.",
    project_root=Path.cwd(),  # 设置项目根目录以自动发现文件
    auto_discover=True,  # 自动发现 AGENTS.md 和 MEMORY.md
)

# 创建构建器
builder = SystemPromptBuilder(config)

# 添加自定义源
security_source = SystemPromptSource(
    name="security",
    priority=100,
    content="Never execute destructive operations without confirmation.",
)
builder.add_source(security_source)

# 构建最终提示
system_prompt = builder.build()
print(f"系统提示长度: {len(system_prompt)} 字符")
```

### discover_project_context() 函数

```python
from harness.memory.system_prompt import discover_project_context

# 自动发现项目上下文
context = discover_project_context(Path.cwd())
if "AGENTS.md" in context:
    print(f"发现 AGENTS.md: {len(context['AGENTS.md'])} 字符")
if "MEMORY.md" in context:
    print(f"发现 MEMORY.md: {len(context['MEMORY.md'])} 字符")
```

## 记忆后端

Harness 支持多种记忆存储后端：

| 后端 | 说明 | 适用场景 |
|------|------|----------|
| **文件系统** | 默认，使用 JSON/YAML 文件 | 开发、小规模 |
| **SQLite** | 轻量数据库 | 中等规模 |
| **向量存储** | 语义搜索 | 大规模、需要检索 |

```python
from harness import AgentHarness

# 默认文件系统后端
agent = AgentHarness(memory_dir=".harness/memory")

# 启用向量检索
agent = AgentHarness(
    memory_dir=".harness/memory",
    vector_store=True,  # 自动创建 VectorMemoryStore
)
```

## 上下文压缩

当工作记忆超过阈值时，Agent Loop 自动触发压缩：

1. 保留最近 N 条消息
2. 将更早的消息压缩为摘要
3. 摘要替换原始消息，释放上下文空间
4. 原始消息仍可通过向量检索访问

```python
# 在 AgentHarness 中配置压缩阈值
from harness import AgentHarness, HarnessConfig

config = HarnessConfig(
    max_input_tokens=100000,  # 最大输入 token 数
    # 当 token 数超过此阈值时自动触发压缩
)
agent = AgentHarness(config=config)

# Ralph Loop 中自动压缩
# 当 token 数超过 compression_threshold 时自动触发
```

## 与技能系统的集成

记忆系统与技能系统紧密集成：

1. **技能加载**：ProgressiveSkillLoader 根据上下文预算决定加载级别
2. **MEMORY.md**：技能执行过程中的经验可保存为记忆
3. **向量检索**：技能内容被索引用于语义搜索
4. **系统提示**：技能指令通过 SystemPromptBuilder 注入系统提示

```python
from harness.memory.memory_file import MemoryFileManager, MemoryEntry, MemoryCategory, MemorySource
from harness.memory.vector_store import VectorMemoryStore
from harness.types import HookPoint, HookContext

# 技能经验保存为记忆
@agent.hook(HookPoint.AFTER_TOOL_EXECUTE)
async def save_skill_experience(ctx: HookContext):
    if ctx.tool_result and ctx.tool_result.is_error:
        # 将错误经验保存到 MEMORY.md
        manager = MemoryFileManager()
        entry = MemoryEntry(
            category=MemoryCategory.LEARNED_PATTERNS,
            content=f"Avoid {ctx.tool_name} when {ctx.tool_result.error} occurs",
            source=MemorySource.AGENT_OBSERVATION,
            metadata={
                "skill": "code-review",
                "error": ctx.tool_result.error,
                "tool": ctx.tool_name,
            }
        )
        manager.add_entry(entry)
    
    # 向量检索技能内容
    if ctx.tool_name == "code_review":
        vector_store = VectorMemoryStore()
        await vector_store.add_skill(
            skill_name="code_review_pattern",
            content=f"Code review pattern: {ctx.tool_result.content[:100]}...",
            metadata={"session_id": ctx.session_id}
        )
    
    return ctx
```

## 全局记忆配置

Harness SDK 支持配置全局记忆文件路径，让 Agent 自动加载全局 MEMORY.md 文件。

### 配置方式

```python
from harness import AgentHarness, HarnessConfig
from pathlib import Path

# 方式 1：通过 HarnessConfig 配置
config = HarnessConfig(
    model="claude-sonnet-4-6",
    memory_md_path=Path.home() / ".harness" / "MEMORY.md",  # 全局记忆文件路径
)
agent = AgentHarness(config=config)

# 方式 2：通过 ContextBuilder 添加自定义记忆源
from harness.memory.system_prompt import SystemPromptSource

agent = AgentHarness(model="claude-sonnet-4-6")
agent._context_builder.add_prompt_source(SystemPromptSource(
    name="GlobalMemory",
    priority=40,
    file_path=Path.home() / ".harness" / "MEMORY.md",
))
```

### 配置项说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `memory_md_path` | `Path \| None` | `None` | 全局 MEMORY.md 文件路径，设置后自动加载到上下文 |

### 使用场景

- **用户偏好存储**：保存用户常用的编码风格、语言偏好等
- **跨项目知识共享**：在多个项目间共享通用的技术决策和模式
- **客户端集成**：桌面客户端可通过 UI 管理全局记忆
- **即时更新**：MEMORY.md 修改后在下一次 run() 调用时自动生效

---

## 记忆评分与衰减机制

基于 Mem0 的 Recency-Aware Ranking 和 Bjork 新遗忘理论，Harness 实现了智能的记忆生命周期管理。

### 核心理念

**不删除记忆，只影响检索排序**。这遵循 Bjork 新遗忘理论的两个强度概念：

- **Storage Strength (importance)**：创建时决定，之后不再变化，用于归档决策
- **Retrieval Strength**：动态变化（时间衰减 + 访问恢复），用于检索排序

### 分层记忆架构

```
Layer 1: Core Memory (MEMORY.md) = Agent 的 "RAM"
- 用户偏好、项目约定
- 始终注入系统提示（无条件可见）
- 不需要检索，不需要 Retrieval Strength
- 容量超限时 Archive 到 Retrieved Memory（不丢失）

Layer 2: Retrieved Memory (VectorMemoryStore) = Agent 的 "Hard Drive"
- 历史对话、特定事件、已归档记忆
- 查询时按需检索
- 需要 Retrieval Strength 加权排序
```

### Retrieval Strength 计算

```
检索分数 = 语义相似度 × Retrieval Strength

Retrieval Strength = 时间衰减因子 × 访问奖励因子

其中：
- 时间衰减因子 = min_strength + (1 - min_strength) × e^(-λ × 未访问天数)
  - 最近访问：≈ 1.0（接近满分）
  - 长期未访问：→ 0.3（保底分数，默认 min_strength=0.3）
- 访问奖励因子 = 1 + 0.5 × log(1 + access_count)
  - 从未访问：1.0
  - 访问 10 次：≈ 2.0
  - 访问 100 次：≈ 2.5
```

**关键设计**：最低 0.3× 保底分数确保旧记忆仍能被检索，只是排序靠后。

### MemoryEntry 增强

```python
@dataclass
class MemoryEntry:
    # 现有字段
    category: MemoryCategory
    content: str
    source: MemorySource
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    # 新增字段（向后兼容）
    importance: float = 1.0           # Storage Strength（用于归档决策）
    last_accessed: datetime | None = None  # 最后访问时间
    access_count: int = 0             # 访问次数

    def calculate_retrieval_strength(
        self,
        decay_lambda: float = 0.05,
        min_strength: float = 0.3,
    ) -> float:
        """计算 Retrieval Strength（仅用于 Retrieved Memory）"""
        ...

    def touch(self) -> None:
        """更新访问时间和计数"""
        self.last_accessed = datetime.now()
        self.access_count += 1
```

### MemoryScoringConfig

```python
@dataclass
class MemoryScoringConfig:
    """记忆评分配置"""
    decay_lambda: float = 0.05            # 衰减速度（λ 越大衰减越快）
    min_retrieval_strength: float = 0.3   # 最低检索强度（保底）
    max_core_memory_tokens: int = 2000    # Core Memory 最大 token 数
    enable_llm_evaluation: bool = False   # 是否启用 LLM 评估 importance
    archive_fallback: Literal["file", "delete", "none"] = "file"
    # file: 归档到 MEMORY_ARCHIVE.md（默认，不丢失数据）
    # delete: 直接删除（不推荐）
    # none: 禁用归档，Core Memory 无限增长
```

### 使用配置

```python
from harness import AgentHarness, HarnessConfig
from harness.sdk.config import MemoryScoringConfig

config = HarnessConfig(
    memory_scoring=MemoryScoringConfig(
        decay_lambda=0.05,           # 衰减速度
        max_core_memory_tokens=2000, # Core Memory 容量上限
        enable_llm_evaluation=True,  # 启用 LLM 评估重要性
        archive_fallback="file",     # 无向量数据库时归档到文件
    ),
)
agent = AgentHarness(config=config)
```

---

## Archive 机制

当 Core Memory 超过容量限制时，自动归档低 importance 的 Entry 到 Retrieved Memory。

### 触发时机

**触发时机**：仅 `run()` 时检查并执行。

```python
async def run(self, prompt: str) -> LoopResult:
    # 检查 Core Memory 容量
    is_over, tokens = self._memory_manager.file_store.check_capacity()
    if is_over:
        await self._memory_manager.archive_low_importance()

    # 继续执行 Agent Loop
    ...
```

**不在 `add_entry()` 时标记**，理由：
- 容量检查开销很小（只是计算字符串长度/token）
- 每次都检查确保不遗漏
- 无状态设计更可靠

### 归档策略（Entry 级别）

**关键设计**：归档是 Entry 级别，不是 Section 级别。即使某 Section 有 10 条 Entry，也只归档 importance 最低的那几条。

```python
async def archive_low_importance(self) -> int:
    """
    容量超限时，跨 section 按 importance 归档低分 Entry
    """
    # 收集所有 section 的所有 Entry
    all_entries = []
    for category in MemoryCategory:
        entries = self._load_entries_with_metadata(category)
        for i, entry in enumerate(entries):
            all_entries.append({
                "category": category,
                "index": i,
                "entry": entry,
            })

    # 按 importance 排序（低分优先归档）
    all_entries.sort(key=lambda x: x["entry"].importance)

    archived = 0
    for item in all_entries:
        # 归档到 Retrieved Memory（不丢失）
        await self._archive_entry(item["entry"])

        # 从 Core Memory 删除
        self.remove_entry(item["category"], item["index"] - archived)
        archived += 1

        # 检查容量是否已释放足够
        if self.check_capacity()[1] <= self.MAX_CORE_MEMORY_TOKENS * 0.8:
            break

    return archived
```

### 无向量数据库的降级方案

当用户未配置 VectorMemoryStore 时，归档的 Entry 写入 `MEMORY_ARCHIVE.md` 文件：

```markdown
# Archived Memory

> 以下记忆已从 Core Memory 归档。可通过全文搜索查找。

## User Profile
- [2026-01-15, importance=0.3] 旧偏好：用户曾使用 macOS

## Key Decisions
- [2025-12-01, importance=0.4] 历史决策：选择 Redis 作为缓存

## Learned Patterns
- [2025-11-15, importance=0.2] 临时模式：用户当时偏好简短回复

## Project Context
- [2025-10-01, importance=0.3] 过时信息：项目使用 Python 3.9
```

### 行为对比

| 场景 | VectorMemoryStore | MEMORY_ARCHIVE.md |
|------|-------------------|-------------------|
| **数据丢失** | 不丢失 | 不丢失 |
| **检索方式** | 语义搜索 | 全文搜索/手动查看 |
| **Retrieval Strength** | 适用 | 不适用 |
| **Agent 自动访问** | 是（通过 search()） | 否（需手动查看文件） |

---

## Importance 的来源与评估

### Importance 的生命周期

```
1. 创建时：LLM 评估（或默认值 1.0）
   ↓
2. 存储后：不再变化（Storage Strength 是静态的）
   ↓
3. 归档决策：按 importance 排序，低分优先归档
```

### LLM 评估触发时机

**异步评估**：添加 Entry 后，后台异步评估 importance，不阻塞主流程。

```python
async def add_entry_async(
    self,
    entry: MemoryEntry,
    llm_client: LLMClient | None = None,
) -> None:
    # 先添加（importance=1.0）
    self._entries.append(entry)
    self._save()

    # 后台评估
    if self.config.enable_llm_evaluation and llm_client:
        importance = await self._evaluate_importance(entry, llm_client)
        entry.importance = importance
        self._save()
```

### 评估示例

| 记忆内容 | 类别 | LLM 评估结果 | 说明 |
|---------|------|-------------|------|
| "用户使用 Windows" | user_profile | 0.85 | 核心偏好，长期有效 |
| "选择 SQLite 作为存储" | key_decisions | 0.75 | 重要决策 |
| "用户喜欢详细的代码示例" | learned_patterns | 0.6 | 一般有用 |
| "上次讨论了 Python 异步" | project_context | 0.4 | 可能过时 |
| "今天天气很好" | project_context | 0.1 | 快速过时 |

---

## MemoryManager（统一接口）

MemoryManager 是分层记忆架构的统一入口，管理 Core Memory 和 Retrieved Memory。

### 核心接口

```python
class MemoryManager:
    """统一记忆管理器"""

    def __init__(
        self,
        file_store: MemoryFileManager,
        vector_store: VectorMemoryStore | None = None,
        config: MemoryScoringConfig | None = None,
    ):
        self.file_store = file_store
        self.vector_store = vector_store
        self.config = config or MemoryScoringConfig()

    def get_context(self, query: str | None = None) -> str:
        """
        获取完整记忆上下文

        1. Core Memory 永远无条件全量加载
        2. Retrieved Memory 根据 Query 主动检索（如果提供了查询）
        """
        # Core Memory 全量加载
        core_memory = self.file_store.to_context_string()

        # Retrieved Memory 按需检索
        retrieved_memory = ""
        if query and self.vector_store:
            results = await self.vector_store.search(
                query,
                top_k=5,
                apply_decay=True,
            )
            retrieved_memory = self._format_retrieved(results)

        return self._combine(core_memory, retrieved_memory)

    async def add_memory(
        self,
        entry: MemoryEntry,
        target: Literal["core", "retrieved"] = "core",
    ) -> None:
        """
        添加记忆到指定层级

        Args:
            entry: 记忆条目
            target: "core" 添加到 MEMORY.md，"retrieved" 添加到向量存储
        """
        if target == "core":
            self.file_store.add_entry(entry)
        elif target == "retrieved" and self.vector_store:
            await self.vector_store.add(
                id=self._generate_id(),
                content=entry.content,
                metadata={
                    "category": entry.category.value,
                    "importance": entry.importance,
                    "created_at": entry.created_at.isoformat(),
                },
            )

    async def archive_to_retrieved(
        self,
        category: MemoryCategory,
        index: int,
    ) -> bool:
        """
        将 Core Memory 条目归档到 Retrieved Memory

        从 MEMORY.md 移除，存入向量存储（或文件归档），记忆不丢失
        """
        ...
```

---

## UpdateCoreMemoryTool

Agent 可通过工具更新 Core Memory（MEMORY.md）。采用 **Mem0 模式**：显式添加到工具列表。

### 工具定义

```python
class UpdateCoreMemoryTool(Tool):
    """Agent 更新用户偏好/项目约定的工具"""

    @property
    def name(self) -> str:
        return "update_core_memory"

    @property
    def description(self) -> str:
        return (
            "更新用户偏好或项目约定到长期记忆。\n\n"
            "重要规则：\n"
            "1. **提炼内容**：不要存储用户原话，要提炼成简洁的陈述\n"
            "   - 用户说「使用 cmd，不要用 powershell」→ 存储「Shell：使用 cmd（不使用 PowerShell）」\n"
            "   - 用户说「我使用 Windows」→ 存储「操作系统：Windows」\n"
            "2. **避免重复**：添加前先检查是否已有类似记忆，如有则不要重复添加\n"
            "3. **适用场景**：用户提到长期偏好、工作环境、项目约束等\n\n"
            "示例：\n"
            "- 用户：「我习惯用深色主题」→ category=user_profile, content=\"主题偏好：深色\"\n"
            "- 用户：「以后回复简短一点」→ category=learned_patterns, content=\"回复风格：简洁\""
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["user_profile", "key_decisions", "learned_patterns", "project_context"],
                },
                "content": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["add", "remove"],
                },
            },
            "required": ["category", "content", "action"],
        }
```

### 内容提炼规则

工具的 description 引导 Agent 提炼用户原话，而不是直接存储：

| 用户原话 | 提炼后的存储内容 |
|---------|-----------------|
| "使用 cmd，不要用 powershell" | `Shell：使用 cmd（不使用 PowerShell）` |
| "我使用 Windows" | `操作系统：Windows` |
| "我习惯用深色主题" | `主题偏好：深色` |
| "以后回复简短一点" | `回复风格：简洁` |

### 去重机制

`MemoryFileManager.add_entry()` 使用字符级 Jaccard 相似度检测重复：

```python
def add_entry(self, entry: MemoryEntry, check_duplicate: bool = True) -> bool:
    """
    Add a new entry to MEMORY.md.

    Returns:
        True if entry was added, False if skipped as duplicate
    """
    if check_duplicate:
        for existing in section:
            similarity = self._calculate_similarity(entry.content, existing)
            if similarity > 0.7:  # 70% 相似度阈值
                logger.info(f"Skipping duplicate memory: '{entry.content}'")
                return False

    section.append(entry.content)
    self.save(sections)
    return True

def _calculate_similarity(self, text1: str, text2: str) -> float:
    """字符级 bigram Jaccard 相似度，支持中英文混合"""
    ngrams1 = {text1[i:i+2] for i in range(len(text1)-1)}
    ngrams2 = {text2[i:i+2] for i in range(len(text2)-1)}
    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2
    return len(intersection) / len(union)
```

### Metadata 支持

`ToolResult.metadata` 用于传递 UI 刷新信号：

```python
# 添加成功时返回 refresh_memory 信号
return ToolResult(
    tool_call_id="",
    success=True,
    content=f"已添加到 {category.value}: {content}",
    metadata={"refresh_memory": True},  # UI 刷新信号
)
```

客户端收到此信号后会刷新记忆面板显示。

### 使用方式

```python
from harness import AgentHarness
from harness.tools.builtins import UpdateCoreMemoryTool

# 显式添加工具
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[
        UpdateCoreMemoryTool(),  # 显式添加
    ],
)
```

### 触发机制

**主机制**：Agent 在对话过程中自主判断是否需要更新 Core Memory。

```
用户: "我使用的是 Windows"

Agent 内部推理:
1. 识别到这是长期偏好信息
2. 判断应该存入 Core Memory
3. 调用 update_core_memory 工具

→ Tool 被触发，将 "Platform: Windows" 写入 MEMORY.md
```

**可选补充**：CoreMemoryExtractionHook 在对话结束后自动提取遗漏的记忆。

---

## 设计总结

| 特性 | Core Memory (MEMORY.md) | Retrieved Memory (VectorMemoryStore) |
|------|------------------------|-------------------------------------|
| **加载方式** | 全量加载 | 按需检索 |
| **access_count** | 不追踪 | 追踪，影响排序 |
| **Retrieval Strength** | 不适用 | 适用（时间衰减 + 访问奖励） |
| **容量管理** | 按 importance 归档低分 Entry | 无容量限制，检索时排序 |
| **淘汰粒度** | Entry 级别（跨 section） | 不淘汰，只降权 |
| **importance 来源** | LLM 评估（可选） | 从 Core Memory 归档时继承 |
| **无向量数据库时** | 归档到 MEMORY_ARCHIVE.md | 不适用 |
