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

```
```
