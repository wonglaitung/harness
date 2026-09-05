"""
Stuck Detector - Detect when agent is stuck in non-progressing state.

Implements multiple detection strategies:
1. Empty/error detection (zero-cost, always available)
2. Semantic similarity detection (requires embedding model)

The semantic detection uses bge-small-zh-v1.5 by default, optimized for Chinese text.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from harness.types import Message, Session

logger = logging.getLogger(__name__)

# Default embedding model (Chinese optimized)
DEFAULT_EMBEDDING_MODEL = "bge-small-zh-v1.5"


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class StuckDetectorConfig:
    """
    Configuration for stuck detection.

    Attributes:
        enable_semantic: Enable semantic similarity detection
        similarity_threshold: Cosine similarity threshold (0.0-1.0)
        consecutive_rounds: Consecutive similar rounds to trigger stuck
        window_size: Number of recent embeddings to compare against
        min_chars: Minimum characters for embedding (shorter texts are skipped)
    """
    # Core switch
    enable_semantic: bool = False

    # Semantic detection thresholds
    similarity_threshold: float = 0.92
    consecutive_rounds: int = 3
    window_size: int = 6
    min_chars: int = 30


@dataclass
class StuckDetectionResult:
    """
    Result from stuck detection.

    Attributes:
        is_stuck: Whether agent is stuck
        reason: "empty", "error", "semantic_repeat", "no_stuck", "model_unavailable"
        similarity: Max similarity score (if semantic detection ran)
        consecutive_count: Current consecutive similar count
        details: Additional diagnostic information
    """
    is_stuck: bool
    reason: str
    similarity: float | None = None
    consecutive_count: int = 0
    details: dict = field(default_factory=dict)


# =============================================================================
# Utility Functions
# =============================================================================

def _normalize_text(s: str) -> str:
    """Normalize text for embedding."""
    return " ".join(s.strip().split())


def _text_hash(s: str) -> str:
    """Generate hash for text (for caching)."""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    if a is None or b is None:
        return 0.0
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# =============================================================================
# StuckDetector
# =============================================================================

class StuckDetector:
    """
    Detect when agent is stuck using semantic similarity.

    Uses embedding model to detect repetitive outputs that indicate
    the agent is not making progress.

    Example:
        config = StuckDetectorConfig(enable_semantic=True)
        detector = StuckDetector(config)

        # Check after each tool execution
        result = await detector.check(session.id, session.messages, iteration)
        if result.is_stuck:
            # Inject feedback or terminate
            pass
    """

    def __init__(self, config: StuckDetectorConfig | None = None):
        self.config = config or StuckDetectorConfig()

        # Lazy-loaded model
        self._model = None
        self._model_unavailable = False
        self._executor = None

        # Per-session state
        self._windows: dict[str, deque] = {}  # session_id -> deque[embedding]
        self._consecutive: dict[str, int] = {}  # session_id -> consecutive count

        # Embedding cache (text_hash -> embedding)
        self._cache: dict[str, np.ndarray] = {}
        self._cache_order: deque = deque(maxlen=10000)  # LRU eviction

    def _load_model(self) -> bool:
        """
        Lazy load embedding model.

        Returns:
            True if model loaded successfully, False otherwise
        """
        if self._model is not None:
            return True
        if self._model_unavailable:
            return False  # Avoid repeated attempts

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
            logger.info(f"StuckDetector: Loaded {DEFAULT_EMBEDDING_MODEL}")
            return True
        except ImportError:
            logger.warning(
                "StuckDetector: sentence-transformers not installed. "
                "Install with: pip install harness-sdk[stuck]"
            )
            self._model_unavailable = True
            return False
        except Exception as e:
            logger.warning(f"StuckDetector: Failed to load model: {e}")
            self._model_unavailable = True
            return False

    async def _get_embedding(self, text: str) -> np.ndarray | None:
        """
        Get embedding for text, using cache if available.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        h = _text_hash(text)

        # Check cache
        if h in self._cache:
            return self._cache[h]

        # Load model if needed
        if not self._load_model():
            return None

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            if self._executor is None:
                from concurrent.futures import ThreadPoolExecutor
                self._executor = ThreadPoolExecutor(max_workers=1)

            embeddings = await loop.run_in_executor(
                self._executor,
                lambda: self._model.encode([text], convert_to_numpy=True)
            )

            emb = np.asarray(embeddings[0], dtype=np.float32)

            # Cache it
            self._cache[h] = emb
            self._cache_order.append(h)

            return emb
        except Exception as e:
            logger.warning(f"StuckDetector: Embedding failed: {e}")
            return None

    def _extract_texts(self, messages: list[Message]) -> list[str]:
        """
        Extract candidate texts from messages for embedding.

        Prioritizes tool outputs and assistant responses.

        Args:
            messages: List of messages

        Returns:
            List of texts to embed
        """
        candidates = []
        for msg in messages:
            if msg.role in ("tool", "assistant"):
                content = msg.content
                if isinstance(content, str):
                    text = _normalize_text(content)
                elif isinstance(content, list):
                    # Handle structured content
                    text = _normalize_text(str(content))
                else:
                    text = _normalize_text(str(content))

                if len(text) >= self.config.min_chars:
                    candidates.append(text)

        return candidates

    async def check(
        self,
        session_id: str,
        messages: list[Message],
        iteration: int,
    ) -> StuckDetectionResult:
        """
        Check if agent is stuck using semantic similarity.

        Args:
            session_id: Session identifier
            messages: Recent messages (tool outputs, assistant responses)
            iteration: Current iteration number

        Returns:
            StuckDetectionResult with detection outcome
        """
        # Check if semantic detection is enabled
        if not self.config.enable_semantic:
            return StuckDetectionResult(
                is_stuck=False,
                reason="semantic_disabled",
            )

        # Extract candidate texts
        texts = self._extract_texts(messages)
        if not texts:
            return StuckDetectionResult(
                is_stuck=False,
                reason="no_candidates",
                details={"message_count": len(messages)},
            )

        # Combine texts for embedding (one embedding per iteration)
        combined_text = "\n".join(texts[-3:])  # Last 3 messages

        # Get embedding
        embedding = await self._get_embedding(combined_text)
        if embedding is None:
            return StuckDetectionResult(
                is_stuck=False,
                reason="model_unavailable",
            )

        # Get or create window
        window = self._windows.setdefault(
            session_id,
            deque(maxlen=self.config.window_size)
        )

        # Calculate max similarity against window
        max_sim = 0.0
        similarities = []
        for prev_emb in window:
            sim = _cosine_similarity(embedding, prev_emb)
            similarities.append(sim)
            max_sim = max(max_sim, sim)

        # Update window
        window.append(embedding)

        # Update consecutive count
        consecutive = self._consecutive.get(session_id, 0)
        if max_sim >= self.config.similarity_threshold:
            consecutive += 1
        else:
            consecutive = 0
        self._consecutive[session_id] = consecutive

        # Determine if stuck
        is_stuck = consecutive >= self.config.consecutive_rounds

        details = {
            "max_similarity": max_sim,
            "avg_similarity": float(np.mean(similarities)) if similarities else 0.0,
            "window_size": len(window),
            "consecutive": consecutive,
            "text_preview": combined_text[:200],
        }

        if is_stuck:
            return StuckDetectionResult(
                is_stuck=True,
                reason="semantic_repeat",
                similarity=max_sim,
                consecutive_count=consecutive,
                details=details,
            )

        return StuckDetectionResult(
            is_stuck=False,
            reason="no_stuck",
            similarity=max_sim,
            consecutive_count=consecutive,
            details=details,
        )

    def clear_session(self, session_id: str) -> None:
        """
        Clear session state.

        Call when session ends or after feedback injection.

        Args:
            session_id: Session to clear
        """
        self._windows.pop(session_id, None)
        self._consecutive.pop(session_id, None)

    def reset(self) -> None:
        """Reset all state."""
        self._windows.clear()
        self._consecutive.clear()
        self._cache.clear()
        self._cache_order.clear()
