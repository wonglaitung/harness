"""
UpdateMemoryTool - SDK Tool for updating MEMORY.md with processed items.

Records processed projects/articles to avoid duplicate extraction.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Default memory file path: packages/scraper/output/MEMORY.md
DEFAULT_MEMORY_PATH = Path(__file__).parent.parent.parent.parent / "output" / "MEMORY.md"


class UpdateMemoryTool(Tool):
    """Update MEMORY.md with processed items to avoid duplicate extraction."""

    @property
    def name(self) -> str:
        return "update_memory"

    @property
    def description(self) -> str:
        return "Record processed items to MEMORY.md to avoid duplicate extraction in future runs. Call this after saving a One-Pager."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Project/item name",
                            },
                            "category": {
                                "type": "string",
                                "description": "Category (e.g., '新范式/工具', '数据库/基础设施', 'UI/前端', '港股分析')",
                            },
                            "source_url": {
                                "type": "string",
                                "description": "Source URL where discovered",
                            },
                        },
                        "required": ["name"],
                    },
                    "description": "List of processed items to record",
                },
                "date": {
                    "type": "string",
                    "description": "Date for the entry (default: today, format: YYYY-MM-DD)",
                },
            },
            "required": ["items"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        items = arguments.get("items", [])
        date_str = arguments.get("date", datetime.now().strftime("%Y-%m-%d"))

        if not items:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="No items provided to record",
            )

        try:
            memory_path = DEFAULT_MEMORY_PATH
            memory_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing content or create new
            if memory_path.exists():
                content = memory_path.read_text(encoding="utf-8")
            else:
                content = self._create_initial_content()

            # Add new items
            content = self._add_items(content, items, date_str)

            # Write back
            memory_path.write_text(content, encoding="utf-8")

            logger.info(f"Updated memory file: {memory_path} with {len(items)} items")

            return ToolResult(
                tool_call_id="",
                success=True,
                content=f"Recorded {len(items)} items to MEMORY.md:\n" + "\n".join(f"- {item['name']}" for item in items),
            )

        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to update memory: {str(e)}",
            )

    def _create_initial_content(self) -> str:
        """Create initial MEMORY.md content."""
        return """# 已提取的情报项目

记录已处理的 AI 项目和港股分析，避免重复抓取。

## 注意事项

- 成熟项目（vLLM、LangChain、Ollama 等）已通过技能文件排除
- 新范式项目优先级：概念 > 架构 > 工具
- 定期审查，移除已成熟的项目

"""

    def _add_items(self, content: str, items: list[dict], date_str: str) -> str:
        """Add items to MEMORY.md content."""
        # Check if date section exists
        date_header = f"## {date_str} 提取"

        if date_header not in content:
            # Add new date section at the end (before 注意事项 if exists)
            if "## 注意事项" in content:
                content = content.replace(
                    "## 注意事项",
                    f"{date_header}\n\n## 注意事项"
                )
            else:
                content = content.rstrip() + f"\n\n{date_header}\n"

        # Group items by category
        categories: dict[str, list[dict]] = {}
        for item in items:
            category = item.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        # Build new content
        new_lines = []
        for category, category_items in categories.items():
            new_lines.append(f"\n### {category}")
            for item in category_items:
                name = item.get("name", "Unknown")
                source_url = item.get("source_url", "")
                if source_url:
                    new_lines.append(f"- **{name}** - {source_url}")
                else:
                    new_lines.append(f"- **{name}**")

        # Insert after date header
        lines = content.split("\n")
        result_lines = []
        inserted = False

        for i, line in enumerate(lines):
            result_lines.append(line)
            if line.strip() == date_header and not inserted:
                # Insert after the date header
                result_lines.extend(new_lines)
                inserted = True

        return "\n".join(result_lines)
