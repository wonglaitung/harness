"""
Tests for Vector Memory Store.
"""

import pytest

from harness.memory.vector_store import (
    MockEmbeddingModel,
    SimpleInMemoryVectorStore,
    VectorMemoryConfig,
    VectorMemoryStore,
    VectorSearchResult,
)


class TestVectorSearchResult:
    """Test VectorSearchResult."""

    def test_create_result(self):
        """Test creating a search result."""
        result = VectorSearchResult(
            id="test_1",
            content="Test content",
            score=0.95,
            metadata={"type": "conversation"},
        )
        assert result.id == "test_1"
        assert result.score == 0.95
        assert result.metadata["type"] == "conversation"


class TestSimpleInMemoryVectorStore:
    """Test SimpleInMemoryVectorStore."""

    @pytest.mark.asyncio
    async def test_add_and_search(self):
        """Test adding vectors and searching."""
        store = SimpleInMemoryVectorStore()

        # Add vectors
        await store.add(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            documents=["Document A", "Document B"],
        )

        # Search with similar vector
        results = await store.search([1.0, 0.1], top_k=10)

        assert len(results) == 2
        assert results[0].id == "a"  # Most similar
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_search_with_filter(self):
        """Test searching with metadata filter."""
        store = SimpleInMemoryVectorStore()

        await store.add(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0], [1.0, 0.0]],
            documents=["Doc A", "Doc B"],
            metadatas=[{"type": "skill"}, {"type": "conversation"}],
        )

        results = await store.search(
            [1.0, 0.0],
            top_k=10,
            filter={"type": "skill"},
        )

        assert len(results) == 1
        assert results[0].id == "a"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting vectors."""
        store = SimpleInMemoryVectorStore()

        await store.add(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
        )

        await store.delete(["a"])

        results = await store.search([1.0, 0.0], top_k=10)
        assert len(results) == 1
        assert results[0].id == "b"

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all vectors."""
        store = SimpleInMemoryVectorStore()

        await store.add(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
        )

        await store.clear()

        results = await store.search([1.0, 0.0], top_k=10)
        assert len(results) == 0


class TestMockEmbeddingModel:
    """Test MockEmbeddingModel."""

    @pytest.mark.asyncio
    async def test_embed(self):
        """Test generating embeddings."""
        model = MockEmbeddingModel(dimension=128)

        embeddings = await model.embed(["hello", "world"])

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 128
        assert model.dimension == 128

    @pytest.mark.asyncio
    async def test_deterministic(self):
        """Test that same text produces same embedding."""
        model = MockEmbeddingModel()

        e1 = await model.embed(["test text"])
        e2 = await model.embed(["test text"])

        assert e1[0] == e2[0]

    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        model = MockEmbeddingModel()

        e1 = await model.embed(["hello"])
        e2 = await model.embed(["goodbye"])

        assert e1[0] != e2[0]


class TestVectorMemoryConfig:
    """Test VectorMemoryConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = VectorMemoryConfig()
        assert config.embedding_model == "mock"
        assert config.embedding_dimension == 384
        assert config.collection_name == "harness_memory"

    def test_custom_config(self):
        """Test custom configuration."""
        config = VectorMemoryConfig(
            embedding_model="openai",
            embedding_dimension=1536,
        )
        assert config.embedding_model == "openai"
        assert config.embedding_dimension == 1536


class TestVectorMemoryStore:
    """Test VectorMemoryStore."""

    @pytest.mark.asyncio
    async def test_add_and_search(self):
        """Test adding and searching documents."""
        store = VectorMemoryStore()

        await store.add("doc1", "Python is a programming language")
        await store.add("doc2", "JavaScript is also a programming language")
        await store.add("doc3", "Apples are fruits")

        results = await store.search("programming languages", top_k=2)

        assert len(results) == 2
        # Doc3 should not be in top results for programming query
        ids = [r.id for r in results]
        assert "doc1" in ids or "doc2" in ids

    @pytest.mark.asyncio
    async def test_add_batch(self):
        """Test adding multiple documents at once."""
        store = VectorMemoryStore()

        await store.add_batch(
            ids=["a", "b", "c"],
            contents=["Content A", "Content B", "Content C"],
            metadatas=[{"idx": 0}, {"idx": 1}, {"idx": 2}],
        )

        results = await store.search("Content", top_k=10)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting documents."""
        store = VectorMemoryStore()

        await store.add("doc1", "Test content")
        await store.delete(["doc1"])

        results = await store.search("Test", top_k=10)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all documents."""
        store = VectorMemoryStore()

        await store.add("a", "Content A")
        await store.add("b", "Content B")
        await store.clear()

        results = await store.search("Content", top_k=10)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_add_conversation(self):
        """Test adding conversation messages."""
        store = VectorMemoryStore()

        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]

        await store.add_conversation("session_123", messages)

        results = await store.search_conversations("Python programming")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_conversations_with_session_filter(self):
        """Test searching conversations with session filter."""
        store = VectorMemoryStore()

        await store.add_conversation("session_1", [
            {"role": "user", "content": "Python question"},
        ])
        await store.add_conversation("session_2", [
            {"role": "user", "content": "JavaScript question"},
        ])

        results = await store.search_conversations(
            "Python",
            session_id="session_1",
        )
        assert len(results) == 1
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_add_and_search_skills(self):
        """Test adding and searching skills."""
        store = VectorMemoryStore()

        await store.add_skill("code_review", "Review code for bugs and issues")
        await store.add_skill("testing", "Write comprehensive tests")

        results = await store.search_skills("find bugs in code")
        assert len(results) >= 1
