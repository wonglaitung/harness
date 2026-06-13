"""
FetchHNTool - SDK Tool for Hacker News fetching.

Wraps the existing HackerNewsSource and ShowHNSource as SDK Tools.
"""

import logging
from datetime import datetime
from typing import Any

import aiohttp

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class FetchHNTool(Tool):
    """Fetch top stories from Hacker News."""

    @property
    def name(self) -> str:
        return "fetch_hn"

    @property
    def description(self) -> str:
        return "Fetch top stories from Hacker News with minimum points threshold. Returns list of posts with title, URL, and points."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "min_points": {
                    "type": "integer",
                    "description": "Minimum points threshold (default: 150)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stories to fetch (default: 20)",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        min_points = arguments.get("min_points", 150)
        limit = arguments.get("limit", 20)

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch top story IDs
                async with session.get(f"{HN_API_BASE}/topstories.json") as resp:
                    if resp.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"HN API error: HTTP {resp.status}",
                        )
                    story_ids = await resp.json()

                # Fetch story details
                posts = []
                for story_id in story_ids[:100]:  # Check up to 100 stories
                    if len(posts) >= limit:
                        break

                    try:
                        async with session.get(f"{HN_API_BASE}/item/{story_id}.json") as resp:
                            if resp.status == 200:
                                story = await resp.json()
                                if story and story.get("url") and story.get("title"):
                                    score = story.get("score", 0)
                                    if score >= min_points:
                                        title = story.get("title", "Untitled")
                                        url = story.get("url", f"https://news.ycombinator.com/item?id={story['id']}")
                                        posts.append(f"Title: {title}\nURL: {url}\nPoints: {score}\n---")
                    except Exception as e:
                        logger.debug(f"Failed to fetch story {story_id}: {e}")
                        continue

                content = f"Fetched {len(posts)} HN posts with score >= {min_points}:\n\n" + "\n".join(posts)

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=content,
                )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"HN fetch error: {str(e)}",
            )


class FetchShowHNTool(Tool):
    """Fetch Show HN posts with lower points threshold for early new projects."""

    @property
    def name(self) -> str:
        return "fetch_show_hn"

    @property
    def description(self) -> str:
        return "Fetch Show HN posts with lower points threshold (default: 50). Good for discovering early new projects."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "min_points": {
                    "type": "integer",
                    "description": "Minimum points threshold (default: 50)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of posts to fetch (default: 15)",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        min_points = arguments.get("min_points", 50)
        limit = arguments.get("limit", 15)

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch show story IDs
                async with session.get(f"{HN_API_BASE}/showstories.json") as resp:
                    if resp.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"HN API error: HTTP {resp.status}",
                        )
                    story_ids = await resp.json()

                # Fetch story details
                posts = []
                for story_id in story_ids[:100]:
                    if len(posts) >= limit:
                        break

                    try:
                        async with session.get(f"{HN_API_BASE}/item/{story_id}.json") as resp:
                            if resp.status == 200:
                                story = await resp.json()
                                if story and story.get("title"):
                                    score = story.get("score", 0)
                                    if score >= min_points:
                                        title = story.get("title", "Untitled")
                                        url = story.get("url", f"https://news.ycombinator.com/item?id={story['id']}")
                                        posts.append(f"Title: {title}\nURL: {url}\nPoints: {score}\n---")
                    except Exception as e:
                        logger.debug(f"Failed to fetch Show HN story {story_id}: {e}")
                        continue

                content = f"Fetched {len(posts)} Show HN posts with score >= {min_points}:\n\n" + "\n".join(posts)

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=content,
                )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Show HN fetch error: {str(e)}",
            )