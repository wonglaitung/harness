"""
Memory Manager - Unified interface for layered memory architecture.

Provides a single entry point for:
- Core Memory (MEMORY.md): Always loaded, no retrieval needed
- Retrieved Memory (VectorMemoryStore): On-demand retrieval with Retrieval Strength

Usage:
    from harness.memory.manager import MemoryManager
    from harness.memory.memory_file import MemoryFileManager
    from harness.memory.vector_store import VectorMemoryStore

    # With vector store
    manager = MemoryManager(
        file_store=MemoryFileManager(project_root=Path.cwd()),
        vector_store=VectorMemoryStore(),
    )

    # Without vector store (file-only mode)
    manager = MemoryManager(
        file_store=MemoryFileManager(project_root=Path.cwd()),
    )

    # Get context for LLM
    context = await manager.get_context(query="async programming")

    # Add memory
    await manager.add_memory(entry, target="core")

    # Archive when capacity exceeded
    await manager.archive_low_importance()
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from harness.memory.memory_file import (
    MemoryCategory,
    MemoryEntry,
    MemoryFileManager,
    MemoryScoringConfig,
)

if TYPE_CHECKING:
    from harness.memory.vector_store import VectorMemoryStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Unified memory manager for layered memory architecture.

    Layer 1: Core Memory (MEMORY.md) = Agent's "RAM"
    - User preferences, project conventions
    - Always injected into system prompt
    - No retrieval needed, no Retrieval Strength

    Layer 2: Retrieved Memory (VectorMemoryStore) = Agent's "Hard Drive"
    - Historical conversations, archived memories
    - On-demand retrieval with Retrieval Strength weighting

    Example:
        manager = MemoryManager(
            file_store=MemoryFileManager(),
            vector_store=VectorMemoryStore(),
        )

        # Core Memory is always loaded
        context = manager.get_context()

        # Retrieved Memory is loaded on-demand with query
        context = await manager.get_context(query="Python async patterns")
    """

    def __init__(
        self,
        file_store: MemoryFileManager,
        vector_store: VectorMemoryStore | None = None,
        config: MemoryScoringConfig | None = None,
    ):
        """
        Initialize the memory manager.

        Args:
            file_store: Core Memory file manager
            vector_store: Retrieved Memory vector store (optional)
            config: Memory scoring configuration
        """
        self.file_store = file_store
        self.vector_store = vector_store
        self.config = config or MemoryScoringConfig()

    def get_context(self, query: str | None = None) -> str:
        """
        Get complete memory context.

        Core Memory is always fully loaded.
        Retrieved Memory is loaded on-demand if query is provided.

        Args:
            query: Optional query for Retrieved Memory retrieval

        Returns:
            Combined context string for LLM
        """
        # Core Memory is always fully loaded
        core_memory = self.file_store.to_context_string()

        if not query or not self.vector_store:
            return core_memory

        # Retrieved Memory requires async call, return core only for sync method
        logger.warning(
            "get_context() with query requires async. "
            "Use get_context_async() for full retrieval support."
        )
        return core_memory

    async def get_context_async(
        self,
        query: str | None = None,
        top_k: int = 5,
    ) -> str:
        """
        Get complete memory context (async version).

        Core Memory is always fully loaded.
        Retrieved Memory is loaded on-demand if query is provided.

        Args:
            query: Optional query for Retrieved Memory retrieval
            top_k: Maximum Retrieved Memory results

        Returns:
            Combined context string for LLM
        """
        # Core Memory is always fully loaded
        core_memory = self.file_store.to_context_string()

        if not query or not self.vector_store:
            return core_memory

        # Retrieved Memory on-demand retrieval
        results = await self.vector_store.search(
            query,
            top_k=top_k,
            apply_decay=True,
        )

        if not results:
            return core_memory

        # Format retrieved memory
        retrieved_lines = ["\n## Retrieved Memory\n"]
        for result in results:
            retrieved_lines.append(f"- [{result.retrieval_strength:.2f}] {result.content}")

        return core_memory + "\n".join(retrieved_lines)

    async def add_memory(
        self,
        entry: MemoryEntry,
        target: Literal["core", "retrieved"] = "core",
    ) -> None:
        """
        Add memory to specified layer.

        Args:
            entry: Memory entry to add
            target: "core" for MEMORY.md, "retrieved" for vector store
        """
        if target == "core":
            self.file_store.add_entry(entry)
            logger.info(f"Added to Core Memory: {entry.content[:50]}...")

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
            logger.info(f"Added to Retrieved Memory: {entry.content[:50]}...")

    async def archive_to_retrieved(
        self,
        category: MemoryCategory,
        index: int,
    ) -> bool:
        """
        Archive Core Memory entry to Retrieved Memory.

        Entry is moved from MEMORY.md to vector store (or file archive),
        ensuring no data loss.

        Args:
            category: Memory category
            index: Entry index in the category

        Returns:
            True if archived successfully, False if index out of bounds
        """
        entries = self.file_store._load_entries_with_metadata(category)
        if index >= len(entries):
            return False

        entry = entries[index]

        if self.vector_store:
            # Archive to vector store (supports semantic retrieval)
            await self.vector_store.add(
                id=self._generate_id(),
                content=entry.content,
                metadata={
                    "category": entry.category.value,
                    "importance": entry.importance,
                    "archived_from": "core_memory",
                    "archived_at": datetime.now().isoformat(),
                },
            )
            logger.info(f"Archived to vector store: {entry.content[:50]}...")
        else:
            # Fallback: archive to file
            self.file_store._archive_to_file(entry)
            logger.info(f"Archived to file: {entry.content[:50]}...")

        # Remove from Core Memory
        self.file_store.remove_entry(category, index)
        return True

    async def archive_low_importance(self) -> int:
        """
        Archive low-importance entries when capacity exceeded.

        This is called by AgentHarness.run() when Core Memory exceeds limits.

        Returns:
            Number of entries archived
        """
        # Define archive callback for vector store
        async def archive_callback(entry: MemoryEntry) -> None:
            if self.vector_store:
                await self.vector_store.add(
                    id=self._generate_id(),
                    content=entry.content,
                    metadata={
                        "category": entry.category.value,
                        "importance": entry.importance,
                        "archived_from": "core_memory",
                        "archived_at": datetime.now().isoformat(),
                    },
                )

        # Use MemoryFileManager's archive method
        return await self.file_store.archive_low_importance(
            archive_callback=archive_callback if self.vector_store else None,
        )

    def check_capacity(self) -> tuple[bool, int]:
        """
        Check if Core Memory exceeds capacity.

        Returns:
            Tuple of (is_over_limit, current_tokens)
        """
        return self.file_store.check_capacity()

    def _generate_id(self) -> str:
        """Generate unique ID for memory entries."""
        return f"mem_{uuid.uuid4().hex[:12]}"


def create_memory_manager(
    project_root: Path | None = None,
    enable_vector_store: bool = False,
    config: MemoryScoringConfig | None = None,
) -> MemoryManager:
    """
    Factory function to create a MemoryManager.

    Args:
        project_root: Project root directory
        enable_vector_store: Whether to enable vector store
        config: Memory scoring configuration

    Returns:
        Configured MemoryManager instance
    """
    file_store = MemoryFileManager(
        project_root=project_root,
        scoring_config=config,
    )

    vector_store = None
    if enable_vector_store:
        from harness.memory.vector_store import VectorMemoryStore

        vector_store = VectorMemoryStore(
            decay_lambda=config.decay_lambda if config else 0.05,
            min_retrieval_strength=config.min_retrieval_strength if config else 0.3,
        )

    return MemoryManager(
        file_store=file_store,
        vector_store=vector_store,
        config=config,
    )
