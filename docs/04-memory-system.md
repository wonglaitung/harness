# 04 - Memory System 记忆系统

## 概述

Memory System 解决 LLM 无状态问题的上下文管理层，负责会话持久化、上下文构建、记忆压缩和检索。

## 架构设计

### 记忆层级模型

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory System                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 1: Working Memory (Immediate)                  │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Current     │ │ Recent      │ │ Active      │     │   │
│  │ │ Conversation│ │ Messages    │ │ Task State  │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 每次调用必需，不可压缩                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 2: Session Memory (Cross-turn)                 │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Session     │ │ Key         │ │ Working     │     │   │
│  │ │ Summary     │ │ Decisions   │ │ Notes       │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 轻量摘要，关键信息提取                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 3: Long-term Memory (Persistent)               │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Skills &    │ │ Project     │ │ User        │     │   │
│  │ │ Patterns    │ │ Knowledge   │ │ Preferences │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 持久存储，按需加载                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 4: Retrieved Memory (On-demand)                │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Vector      │ │ Semantic    │ │ Historical  │     │   │
│  │ │ Search      │ │ Lookup      │ │ Context     │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 检索式加载，仅加载相关内容                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入
    │
    ↓
┌─────────────────┐
│   Trigger       │
│   Manager       │
└────────┬────────┘
         │ Session ID
         ↓
┌─────────────────────────────────────────────────────┐
│                 Memory Manager                       │
│                                                      │
│  1. Load Session (SessionStore)                     │
│  2. Get Working Memory (last N messages)            │
│  3. Get Session Summary                             │
│  4. Get Skills & Knowledge                          │
│  5. Retrieve Relevant Context                       │
│                                                      │
│  Output: Context object                             │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
              ┌─────────────┐
              │ Context     │
              │ Builder     │
              │             │
              │ - 预算分配   │
              │ - Token 计数 │
              │ - 压缩判断   │
              └─────────────┘
                     │
                     ↓
              ┌─────────────┐
              │   Agent     │
              │   Loop      │
              └─────────────┘
                     │
                     ↓
              ┌─────────────┐
              │ Memory      │
              │ Update      │
              │             │
              │ - 保存消息   │
              │ - 更新摘要   │
              │ - 学习模式   │
              └─────────────┘
```

## 核心组件

### 4.1 Session Management

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

@dataclass
class Message:
    """消息"""
    role: str  # "user", "assistant", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_call_id": self.tool_call_id,
            "metadata": self.metadata
        }

@dataclass
class Session:
    """会话"""
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    working_directory: str = ""
    user_id: Optional[str] = None

    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """获取最近 N 条消息"""
        return self.messages[-n:]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "metadata": self.metadata,
            "working_directory": self.working_directory,
            "user_id": self.user_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data["messages"]],
            summary=data.get("summary"),
            metadata=data.get("metadata", {}),
            working_directory=data.get("working_directory", ""),
            user_id=data.get("user_id")
        )
```

### 4.2 Session Store

```python
from abc import ABC, abstractmethod
import os
import json
from pathlib import Path

class SessionStore(ABC):
    """会话存储抽象"""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """保存会话"""
        pass

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """删除会话"""
        pass

    @abstractmethod
    async def list_sessions(self, user_id: str = None) -> List[str]:
        """列出会话"""
        pass


class FileSessionStore(SessionStore):
    """文件存储实现"""

    def __init__(self, storage_dir: str = "~/.harness/sessions"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    async def save(self, session: Session) -> None:
        """保存会话到文件"""
        path = self._session_path(session.id)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    async def load(self, session_id: str) -> Optional[Session]:
        """从文件加载会话"""
        path = self._session_path(session_id)
        if not path.exists():
            return None

        with open(path, "r") as f:
            data = json.load(f)
            return Session.from_dict(data)

    async def delete(self, session_id: str) -> None:
        """删除会话文件"""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()

    async def list_sessions(self, user_id: str = None) -> List[str]:
        """列出所有会话 ID"""
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            sessions.append(path.stem)
        return sessions


class SQLiteSessionStore(SessionStore):
    """SQLite 存储"""

    def __init__(self, db_path: str = "~/.harness/harness.db"):
        import aiosqlite

        self.db_path = Path(db_path).expanduser()
        self._initialized = False

    async def _init_db(self):
        if self._initialized:
            return

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    user_id TEXT,
                    working_directory TEXT,
                    summary TEXT,
                    metadata TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            await db.commit()

        self._initialized = True

    async def save(self, session: Session) -> None:
        await self._init_db()

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            # 保存会话
            await db.execute("""
                INSERT OR REPLACE INTO sessions
                (id, created_at, updated_at, user_id, working_directory, summary, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.user_id,
                session.working_directory,
                session.summary,
                json.dumps(session.metadata)
            ))

            # 删除旧消息
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session.id,))

            # 保存新消息
            for msg in session.messages:
                await db.execute("""
                    INSERT INTO messages
                    (session_id, role, content, timestamp, tool_calls, tool_call_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.id,
                    msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    json.dumps([tc.to_dict() for tc in msg.tool_calls]),
                    msg.tool_call_id,
                    json.dumps(msg.metadata)
                ))

            await db.commit()

    async def load(self, session_id: str) -> Optional[Session]:
        await self._init_db()

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            # 加载会话
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            session = Session(
                id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                user_id=row[3],
                working_directory=row[4],
                summary=row[5],
                metadata=json.loads(row[6])
            )

            # 加载消息
            cursor = await db.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,)
            )
            for msg_row in await cursor.fetchall():
                session.messages.append(Message(
                    role=msg_row[1],
                    content=msg_row[2],
                    timestamp=datetime.fromisoformat(msg_row[3]),
                    tool_calls=json.loads(msg_row[4]),
                    tool_call_id=msg_row[5],
                    metadata=json.loads(msg_row[6])
                ))

            return session
```

### 4.3 Context Builder

```python
@dataclass
class ContextBudget:
    """上下文预算"""
    max_tokens: int
    reserved_for_output: int = 4096
    reserved_for_tools: int = 2000

    @property
    def available_for_input(self) -> int:
        return self.max_tokens - self.reserved_for_output - self.reserved_for_tools


@dataclass
class ContextComponents:
    """上下文组件"""
    system_prompt: str = ""
    skills_prompt: str = ""
    recent_messages: List[Message] = field(default_factory=list)
    session_summary: str = ""
    memory_content: str = ""
    retrieved_content: str = ""
    tool_schemas: List[ToolSchema] = field(default_factory=list)


@dataclass
class Context:
    """构建完成的上下文"""
    system_prompt: str
    messages: List[Message]
    tools: List[ToolSchema]
    token_count: int
    components: ContextComponents


class ContextBuilder:
    """上下文构建器"""

    def __init__(
        self,
        token_counter: TokenCounter,
        budget: ContextBudget,
        compression_threshold: float = 0.8
    ):
        self.counter = token_counter
        self.budget = budget
        self.compression_threshold = compression_threshold

    async def build(
        self,
        messages: List[Message],
        session: Session,
        skills: List[Skill] = None,
        tools: List[ToolSchema] = None,
        memory_content: str = ""
    ) -> Context:
        """构建上下文"""

        # 估算各组件 token
        components = ContextComponents(
            recent_messages=messages[-10:],  # 默认保留最近 10 条
            tool_schemas=tools or []
        )

        # 构建系统提示
        components.system_prompt = self._build_system_prompt(session)
        components.skills_prompt = self._build_skills_prompt(skills or [])
        components.session_summary = session.summary or ""

        # 计算当前 token 数
        current_tokens = self._estimate_tokens(components)

        # 检查是否需要压缩
        if current_tokens > self.budget.available_for_input * self.compression_threshold:
            components = await self._compress_context(components)

        # 构建最终上下文
        final_messages = self._build_messages(components)

        return Context(
            system_prompt=self._combine_prompts(components),
            messages=final_messages,
            tools=components.tool_schemas,
            token_count=self.counter.count_messages(final_messages),
            components=components
        )

    def _build_system_prompt(self, session: Session) -> str:
        """构建基础系统提示"""
        return """You are an AI assistant with access to tools.
When you need to perform an action, use the appropriate tool.
Think carefully about which tools to use and provide clear reasoning."""

    def _build_skills_prompt(self, skills: List[Skill]) -> str:
        """构建技能提示"""
        if not skills:
            return ""

        prompts = []
        for skill in skills:
            prompts.append(f"""
## {skill.name}
{skill.content}
""")
        return "\n".join(prompts)

    def _combine_prompts(self, components: ContextComponents) -> str:
        """合并所有提示"""
        parts = [components.system_prompt]

        if components.skills_prompt:
            parts.append("\n# Skills\n" + components.skills_prompt)

        if components.session_summary:
            parts.append("\n# Session Summary\n" + components.session_summary)

        return "\n".join(parts)

    def _build_messages(self, components: ContextComponents) -> List[Message]:
        """构建消息列表"""
        # 可以添加摘要作为系统消息
        messages = []

        if components.session_summary:
            # 在旧消息之前插入摘要
            messages.append(Message(
                role="system",
                content=f"[Previous conversation summary]\n{components.session_summary}"
            ))

        messages.extend(components.recent_messages)

        return messages

    def _estimate_tokens(self, components: ContextComponents) -> int:
        """估算总 token 数"""
        total = 0

        total += self.counter.count(components.system_prompt)
        total += self.counter.count(components.skills_prompt)
        total += self.counter.count(components.session_summary)

        for msg in components.recent_messages:
            total += self.counter.count(msg.content)
            total += 50  # 消息格式开销

        for tool in components.tool_schemas:
            total += 100  # 工具 schema 估算
            total += self.counter.count(json.dumps(tool.parameters)) // 4

        return total

    async def _compress_context(
        self,
        components: ContextComponents
    ) -> ContextComponents:
        """压缩上下文"""

        # 策略 1: 减少最近消息数量
        if len(components.recent_messages) > 5:
            # 摘要旧消息
            old_messages = components.recent_messages[:-5]
            summary = await self._summarize_messages(old_messages)
            components.session_summary = (
                components.session_summary + "\n" + summary
                if components.session_summary
                else summary
            )
            components.recent_messages = components.recent_messages[-5:]

        # 策略 2: 压缩技能提示
        if len(components.skills_prompt) > 1000:
            components.skills_prompt = components.skills_prompt[:1000]

        return components

    async def _summarize_messages(
        self,
        messages: List[Message]
    ) -> str:
        """摘要消息"""
        # 可以使用 LLM 生成摘要，或简单的格式化
        summary_parts = []
        for msg in messages:
            if msg.role == "user":
                summary_parts.append(f"User asked: {msg.content[:100]}")
            elif msg.role == "assistant":
                summary_parts.append(f"Assistant: {msg.content[:100]}")

        return "\n".join(summary_parts)
```

### 4.4 Memory Store

```python
@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    type: str  # "skill", "pattern", "preference", "knowledge"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    relevance_score: float = 0.0


class MemoryStore(ABC):
    """记忆存储抽象"""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """存储记忆"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """检索记忆"""
        pass

    @abstractmethod
    async def get_all(self, type: str = None) -> List[MemoryEntry]:
        """获取所有记忆"""
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> None:
        """删除记忆"""
        pass


class FileMemoryStore(MemoryStore):
    """文件记忆存储"""

    def __init__(self, memory_dir: str = "~/.harness/memory"):
        self.memory_dir = Path(memory_dir).expanduser()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.memory_dir / "index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file) as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def _entry_path(self, entry_id: str) -> Path:
        return self.memory_dir / f"{entry_id}.md"

    async def store(self, entry: MemoryEntry) -> None:
        path = self._entry_path(entry.id)

        # 写入内容
        content = f"""---
id: {entry.id}
type: {entry.type}
created_at: {entry.created_at.isoformat()}
updated_at: {entry.updated_at.isoformat()}
metadata: {json.dumps(entry.metadata)}
---

{entry.content}
"""
        with open(path, "w") as f:
            f.write(content)

        # 更新索引
        self.index[entry.id] = {
            "type": entry.type,
            "path": str(path),
            "created_at": entry.created_at.isoformat()
        }
        self._save_index()

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """简单的关键词检索"""
        results = []

        for entry_id, info in self.index.items():
            if types and info["type"] not in types:
                continue

            path = self._entry_path(entry_id)
            if path.exists():
                content = path.read_text()

                # 简单关键词匹配
                if query.lower() in content.lower():
                    # 解析并返回
                    results.append(self._parse_entry(content))

        return results[:limit]

    def _parse_entry(self, content: str) -> MemoryEntry:
        """解析记忆文件"""
        import yaml

        parts = content.split("---\n")
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2]

            return MemoryEntry(
                id=frontmatter["id"],
                type=frontmatter["type"],
                content=body,
                metadata=frontmatter.get("metadata", {}),
                created_at=datetime.fromisoformat(frontmatter["created_at"]),
                updated_at=datetime.fromisoformat(frontmatter["updated_at"])
            )

        return MemoryEntry(id="unknown", type="unknown", content=content)
```

### 4.5 Vector Retrieval (RAG)

```python
class VectorMemoryStore(MemoryStore):
    """向量检索记忆存储"""

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        vector_db: str = "chroma"
    ):
        self.embedding_model = embedding_model

        # 初始化向量数据库
        if vector_db == "chroma":
            import chromadb
            self.client = chromadb.PersistentClient("~/.harness/vectors")
            self.collection = self.client.get_or_create_collection("memory")

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        # 使用 OpenAI 或本地模型
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        response = await client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def store(self, entry: MemoryEntry) -> None:
        """存储记忆并建立向量索引"""
        embedding = await self._get_embedding(entry.content)

        self.collection.add(
            ids=[entry.id],
            embeddings=[embedding],
            documents=[entry.content],
            metadatas=[{
                "type": entry.type,
                "created_at": entry.created_at.isoformat(),
                **entry.metadata
            }]
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """向量相似度检索"""
        query_embedding = await self._get_embedding(query)

        where_filter = None
        if types:
            where_filter = {"type": {"$in": types}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter
        )

        entries = []
        for i, doc in enumerate(results["documents"][0]):
            entries.append(MemoryEntry(
                id=results["ids"][0][i],
                type=results["metadatas"][0][i]["type"],
                content=doc,
                metadata=results["metadatas"][0][i],
                relevance_score=1 - results["distances"][0][i]
            ))

        return entries
```

### 4.6 Context Compression

```python
class ContextCompressor:
    """上下文压缩器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def compress_session(
        self,
        session: Session,
        target_tokens: int
    ) -> str:
        """压缩会话为摘要"""

        # 构建所有消息的文本
        all_messages = "\n".join([
            f"{m.role}: {m.content}"
            for m in session.messages
        ])

        prompt = f"""Summarize the following conversation, preserving:
1. Key decisions made
2. Important context established
3. Outstanding tasks or questions
4. User preferences discovered

Conversation:
{all_messages}

Summary (concise, under {target_tokens // 4} words):"""

        response = await self.llm.call(
            Context(
                system_prompt="You are a concise summarizer.",
                messages=[Message(role="user", content=prompt)],
                tools=[]
            )
        )

        return response.message.content

    async def compress_tool_results(
        self,
        results: List[ToolResult],
        max_length: int = 2000
    ) -> str:
        """压缩工具结果"""

        if not results:
            return ""

        # 简单截断或智能摘要
        combined = "\n".join([r.content[:500] for r in results])

        if len(combined) > max_length:
            # 使用 LLM 摘要
            prompt = f"""Summarize these tool results concisely:

{combined}

Summary:"""

            response = await self.llm.call(
                Context(
                    system_prompt="Summarize tool results.",
                    messages=[Message(role="user", content=prompt)],
                    tools=[]
                )
            )
            return response.message.content

        return combined


class AutoCompressor:
    """自动压缩管理器"""

    def __init__(
        self,
        compressor: ContextCompressor,
        threshold_ratio: float = 0.8,
        min_messages_before_compress: int = 20
    ):
        self.compressor = compressor
        self.threshold_ratio = threshold_ratio
        self.min_messages = min_messages_before_compress

    async def should_compress(
        self,
        session: Session,
        current_tokens: int,
        max_tokens: int
    ) -> bool:
        """判断是否需要压缩"""
        if len(session.messages) < self.min_messages:
            return False

        return current_tokens > max_tokens * self.threshold_ratio

    async def auto_compress(
        self,
        session: Session,
        max_tokens: int
    ) -> Session:
        """自动压缩会话"""

        # 保留最近消息，压缩旧消息
        keep_recent = 10
        old_messages = session.messages[:-keep_recent]

        if not old_messages:
            return session

        # 生成摘要
        summary = await self.compressor.compress_session(
            Session(id=session.id, messages=old_messages),
            target_tokens=500
        )

        # 更新会话
        session.summary = (
            session.summary + "\n\n" + summary
            if session.summary
            else summary
        )
        session.messages = session.messages[-keep_recent:]

        return session
```

## Memory Manager

```python
@dataclass
class MemoryConfig:
    """记忆配置"""
    storage_type: str = "file"  # file, sqlite, redis
    storage_path: str = "~/.harness"
    enable_vector_search: bool = False
    embedding_model: str = "text-embedding-3-small"
    max_session_messages: int = 100
    compression_threshold: float = 0.8
    auto_compress: bool = True


class MemoryManager:
    """记忆管理器"""

    def __init__(
        self,
        config: MemoryConfig,
        llm_client: LLMClient = None
    ):
        self.config = config

        # 初始化存储
        if config.storage_type == "file":
            self.session_store = FileSessionStore(
                f"{config.storage_path}/sessions"
            )
            self.memory_store = FileMemoryStore(
                f"{config.storage_path}/memory"
            )
        elif config.storage_type == "sqlite":
            self.session_store = SQLiteSessionStore(
                f"{config.storage_path}/harness.db"
            )
            self.memory_store = FileMemoryStore(
                f"{config.storage_path}/memory"
            )

        # 向量检索
        if config.enable_vector_search:
            self.vector_store = VectorMemoryStore(
                embedding_model=config.embedding_model
            )
        else:
            self.vector_store = None

        # 压缩器
        self.compressor = ContextCompressor(llm_client) if llm_client else None
        self.auto_compressor = AutoCompressor(
            self.compressor,
            threshold_ratio=config.compression_threshold
        ) if self.compressor else None

        # Token 计数器
        self.token_counter = TokenCounter()

        # 上下文构建器
        self.context_builder = ContextBuilder(
            self.token_counter,
            ContextBudget(max_tokens=200000)
        )

    async def create_session(
        self,
        user_id: str = None,
        working_directory: str = ""
    ) -> Session:
        """创建新会话"""
        session_id = self._generate_session_id()

        session = Session(
            id=session_id,
            user_id=user_id,
            working_directory=working_directory
        )

        await self.session_store.save(session)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return await self.session_store.load(session_id)

    async def update_session(self, session: Session) -> None:
        """更新会话"""
        # 检查是否需要压缩
        if self.auto_compressor and self.config.auto_compress:
            current_tokens = self.token_counter.count_messages(session.messages)
            if await self.auto_compressor.should_compress(
                session, current_tokens, 200000
            ):
                session = await self.auto_compressor.auto_compress(session, 200000)

        await self.session_store.save(session)

    async def build_context(
        self,
        session: Session,
        skills: List[Skill] = None,
        tools: List[ToolSchema] = None
    ) -> Context:
        """构建上下文"""
        return await self.context_builder.build(
            messages=session.messages,
            session=session,
            skills=skills,
            tools=tools
        )

    async def store_memory(
        self,
        type: str,
        content: str,
        metadata: Dict = None
    ) -> MemoryEntry:
        """存储记忆"""
        entry_id = self._generate_memory_id()

        entry = MemoryEntry(
            id=entry_id,
            type=type,
            content=content,
            metadata=metadata or {}
        )

        await self.memory_store.store(entry)

        if self.vector_store:
            await self.vector_store.store(entry)

        return entry

    async def retrieve_memory(
        self,
        query: str,
        types: List[str] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """检索记忆"""
        if self.vector_store:
            return await self.vector_store.retrieve(query, limit, types)
        else:
            return await self.memory_store.retrieve(query, limit, types)

    def _generate_session_id(self) -> str:
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"

    def _generate_memory_id(self) -> str:
        import uuid
        return f"memory_{uuid.uuid4().hex[:8]}"
```

## 记忆文件格式

### MEMORY.md 格式

```markdown
# MEMORY.md

This file contains persistent memory that is loaded across sessions.

## User Profile

- Role: Software Developer
- Preferred Language: Python
- Project Context: Building a harness framework

## Key Decisions

- 2026-05-28: Decided to use Python as primary language
- 2026-05-28: Chose SQLite for session storage (simple, embedded)

## Learned Patterns

- User prefers concise responses without trailing summaries
- User wants to see file paths and line numbers in code references

## Active Tasks

- Complete design documentation for harness project
- Implement Agent Loop MVP
```

### Session Summary 格式

```markdown
## Session Summary (2026-05-28)

### Key Actions
1. Created project structure in /data/harness
2. Wrote initial design documents (overview, agent-loop, tool-system)
3. Discussed memory system design

### Important Context
- User wants an embeddable harness SDK (not standalone service)
- Similar to Hermes/OpenClaw but for integration

### Pending
- Need to write remaining design docs (skills, triggers, sdk)
- Need to start implementation after design is complete
```

## 测试

```python
import pytest

@pytest.fixture
async def memory_manager():
    config = MemoryConfig(
        storage_type="file",
        storage_path="/tmp/test_harness"
    )
    return MemoryManager(config)

@pytest.mark.asyncio
async def test_session_lifecycle(memory_manager):
    # 创建会话
    session = await memory_manager.create_session()
    assert session.id.startswith("session_")

    # 添加消息
    session.add_message(Message(role="user", content="Hello"))
    await memory_manager.update_session(session)

    # 加载会话
    loaded = await memory_manager.get_session(session.id)
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"

@pytest.mark.asyncio
async def test_memory_storage(memory_manager):
    # 存储记忆
    entry = await memory_manager.store_memory(
        type="preference",
        content="User prefers Python",
        metadata={"category": "language"}
    )

    # 检索记忆
    results = await memory_manager.retrieve_memory("Python")
    assert len(results) > 0
    assert "Python" in results[0].content
```