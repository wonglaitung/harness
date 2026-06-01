"""
Vector Memory Store - Semantic search for conversations, skills, and documents.

This is an optional feature that requires additional dependencies.
Install with: pip install harness-ai[vector]

Provides:
- Semantic search over conversation history
- Skill matching by semantic similarity
- Document retrieval with embeddings
- Pluggable embedding models and vector stores

Usage:
    from harness.memory.vector_store import VectorMemoryStore

    store = VectorMemoryStore(
        embedding_model="text-embedding-3-small",
        persist_dir="~/.harness/vectors",
    )

    # Add documents
    await store.add("session_123", "User asked about Python async patterns")

    # Search
    results = await store.search("async programming", top_k=5)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Result from a vector search."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class EmbeddingModel(Protocol):
    """Protocol for embedding models."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        ...


class VectorStore(Protocol):
    """Protocol for vector stores."""

    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """Add vectors to the store."""
        ...

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors."""
        ...

    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by IDs."""
        ...

    async def clear(self) -> None:
        """Clear all vectors."""
        ...


class SimpleInMemoryVectorStore:
    """
    Simple in-memory vector store for testing and basic use cases.

    Uses cosine similarity for search. Not suitable for production
    with large datasets.
    """

    def __init__(self):
        self._vectors: dict[str, list[float]] = {}
        self._documents: dict[str, str] = {}
        self._metadatas: dict[str, dict[str, Any]] = {}

    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """Add vectors to the store."""
        for i, id_ in enumerate(ids):
            self._vectors[id_] = embeddings[i]
            if documents:
                self._documents[id_] = documents[i]
            if metadatas:
                self._metadatas[id_] = metadatas[i]

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search using cosine similarity."""
        import math

        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        # Calculate similarities
        similarities = []
        for id_, embedding in self._vectors.items():
            # Apply filter if provided
            if filter:
                metadata = self._metadatas.get(id_, {})
                if not all(metadata.get(k) == v for k, v in filter.items()):
                    continue

            score = cosine_similarity(query_embedding, embedding)
            similarities.append((id_, score))

        # Sort by score descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top k results
        results = []
        for id_, score in similarities[:top_k]:
            results.append(VectorSearchResult(
                id=id_,
                content=self._documents.get(id_, ""),
                score=score,
                metadata=self._metadatas.get(id_, {}),
            ))

        return results

    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by IDs."""
        for id_ in ids:
            self._vectors.pop(id_, None)
            self._documents.pop(id_, None)
            self._metadatas.pop(id_, None)

    async def clear(self) -> None:
        """Clear all vectors."""
        self._vectors.clear()
        self._documents.clear()
        self._metadatas.clear()


class MockEmbeddingModel:
    """
    Mock embedding model for testing.

    Generates deterministic embeddings based on text content.
    Not suitable for production use.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings."""
        import hashlib

        embeddings = []
        for text in texts:
            # Use hash of text to generate deterministic embedding
            h = hashlib.sha256(text.encode()).digest()
            embedding = []
            for i in range(self._dimension):
                # Use modulo to cycle through hash bytes
                val = h[i % len(h)] / 255.0 - 0.5
                embedding.append(val)
            embeddings.append(embedding)

        return embeddings

    @property
    def dimension(self) -> int:
        return self._dimension


@dataclass
class VectorMemoryConfig:
    """Configuration for vector memory store."""

    embedding_model: str = "mock"  # "mock", "openai", "sentence-transformers"
    persist_dir: Path | None = None
    collection_name: str = "harness_memory"
    embedding_dimension: int = 384


class VectorMemoryStore:
    """
    Vector-based memory store for semantic search.

    Provides semantic search capabilities over:
    - Conversation history
    - Skill content
    - Documents and notes

    Example:
        store = VectorMemoryStore()
        await store.add_document("doc1", "Python async patterns")

        results = await store.search("concurrency in Python")
        for result in results:
            print(f"{result.score}: {result.content}")
    """

    def __init__(
        self,
        config: VectorMemoryConfig | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
    ):
        """
        Initialize the vector memory store.

        Args:
            config: Configuration for the store
            embedding_model: Custom embedding model (overrides config)
            vector_store: Custom vector store (overrides config)
        """
        self.config = config or VectorMemoryConfig()

        # Initialize embedding model
        if embedding_model:
            self._embedding = embedding_model
        elif self.config.embedding_model == "mock":
            self._embedding = MockEmbeddingModel(self.config.embedding_dimension)
        else:
            # Try to load real embedding model
            self._embedding = self._load_embedding_model()

        # Initialize vector store
        if vector_store:
            self._store = vector_store
        else:
            self._store = SimpleInMemoryVectorStore()

    def _load_embedding_model(self) -> EmbeddingModel:
        """Load embedding model based on configuration."""
        model_name = self.config.embedding_model

        if model_name == "openai":
            try:
                from openai import AsyncOpenAI

                class OpenAIEmbedding:
                    def __init__(self, model: str = "text-embedding-3-small"):
                        self._client = AsyncOpenAI()
                        self._model = model
                        self._dimension = 1536

                    async def embed(self, texts: list[str]) -> list[list[float]]:
                        response = await self._client.embeddings.create(
                            input=texts,
                            model=self._model,
                        )
                        return [e.embedding for e in response.data]

                    @property
                    def dimension(self) -> int:
                        return self._dimension

                return OpenAIEmbedding()
            except ImportError:
                logger.warning("OpenAI not installed, falling back to mock")
                return MockEmbeddingModel()

        elif model_name == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer

                class SentenceTransformerEmbedding:
                    def __init__(self, model: str = "all-MiniLM-L6-v2"):
                        self._model = SentenceTransformer(model)
                        self._dimension = self._model.get_sentence_embedding_dimension()

                    async def embed(self, texts: list[str]) -> list[list[float]]:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        embeddings = await loop.run_in_executor(
                            None,
                            self._model.encode,
                            texts,
                        )
                        return embeddings.tolist()

                    @property
                    def dimension(self) -> int:
                        return self._dimension

                return SentenceTransformerEmbedding()
            except ImportError:
                logger.warning("sentence-transformers not installed, falling back to mock")
                return MockEmbeddingModel()

        else:
            return MockEmbeddingModel()

    async def add(
        self,
        id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a single document to the store.

        Args:
            id: Unique identifier
            content: Text content
            metadata: Optional metadata
        """
        embeddings = await self._embedding.embed([content])
        await self._store.add(
            ids=[id],
            embeddings=embeddings,
            documents=[content],
            metadatas=[metadata or {}],
        )

    async def add_batch(
        self,
        ids: list[str],
        contents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Add multiple documents to the store.

        Args:
            ids: List of unique identifiers
            contents: List of text contents
            metadatas: Optional list of metadata dicts
        """
        embeddings = await self._embedding.embed(contents)
        await self._store.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            top_k: Maximum results to return
            filter: Optional metadata filter

        Returns:
            List of search results sorted by relevance
        """
        # Generate embedding for query
        query_embeddings = await self._embedding.embed([query])
        query_embedding = query_embeddings[0]

        # Search in store
        return await self._store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter,
        )

    async def delete(self, ids: list[str]) -> None:
        """Delete documents by IDs."""
        await self._store.delete(ids)

    async def clear(self) -> None:
        """Clear all documents."""
        await self._store.clear()

    async def add_conversation(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """
        Add conversation messages to the store.

        Args:
            session_id: Session identifier
            messages: List of message dicts with role and content
        """
        ids = []
        contents = []
        metadatas = []

        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if not content:
                continue

            ids.append(f"{session_id}_{i}")
            contents.append(content)
            metadatas.append({
                "session_id": session_id,
                "role": msg.get("role", "user"),
                "type": "conversation",
            })

        if ids:
            await self.add_batch(ids, contents, metadatas)

    async def search_conversations(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        """
        Search conversation history.

        Args:
            query: Search query
            session_id: Optional session filter
            top_k: Maximum results

        Returns:
            List of matching messages
        """
        filter_dict = {"type": "conversation"}
        if session_id:
            filter_dict["session_id"] = session_id

        return await self.search(query, top_k=top_k, filter=filter_dict)

    async def add_skill(
        self,
        skill_name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add skill content to the store.

        Args:
            skill_name: Skill identifier
            content: Skill content
            metadata: Optional metadata
        """
        meta = {"type": "skill", "skill_name": skill_name}
        if metadata:
            meta.update(metadata)

        await self.add(f"skill_{skill_name}", content, meta)

    async def search_skills(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """
        Search skills by semantic similarity.

        Args:
            query: Search query
            top_k: Maximum results

        Returns:
            List of matching skills
        """
        return await self.search(
            query,
            top_k=top_k,
            filter={"type": "skill"},
        )
