"""
UpdateMemoryTool - SDK Tool for updating MEMORY.md with processed items.

Records processed projects/articles to avoid duplicate extraction.

Features:
- Auto-archiving: entries older than 30 days are moved to archive/
- Rolling window: MEMORY.md only keeps recent entries for fast loading
"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"
DEFAULT_MEMORY_PATH = DEFAULT_OUTPUT_DIR / "MEMORY.md"
ARCHIVE_DIR = DEFAULT_OUTPUT_DIR / "archive"

# Keep last N days in MEMORY.md
RETENTION_DAYS = 30


class UpdateMemoryTool(Tool):
    """Update MEMORY.md with processed items to avoid duplicate extraction.

    Features:
    - Records processed items with date, category, and source URL
    - Auto-archives entries older than 30 days to archive/MEMORY-YYYY-MM.md
    - Keeps MEMORY.md small for fast loading
    """

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

            # Auto-archive old entries
            content = self._archive_old_entries(content)

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

    def _archive_old_entries(self, content: str) -> str:
        """
        Archive entries older than RETENTION_DAYS to archive/MEMORY-YYYY-MM.md.

        Args:
            content: Current MEMORY.md content

        Returns:
            Content with old entries removed (archived to separate files)
        """
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)

        # Find all date sections
        date_pattern = re.compile(r'^## (\d{4}-\d{2}-\d{2}) 提取$')
        lines = content.split('\n')

        # Parse sections
        sections: dict[str, list[str]] = {}  # date -> lines
        header_lines: list[str] = []  # Lines before first date section
        footer_lines: list[str] = []  # Lines after last date section (注意事项 etc.)
        current_date: str | None = None
        current_lines: list[str] = []
        in_footer = False

        for line in lines:
            match = date_pattern.match(line.strip())
            if match:
                # Save previous section
                if current_date:
                    sections[current_date] = current_lines
                elif current_lines:
                    header_lines = current_lines
                current_date = match.group(1)
                current_lines = [line]
                in_footer = False
            elif current_date is None:
                # Before any date section
                current_lines.append(line)
            elif line.strip().startswith('## 注意事项') or line.strip().startswith('## '):
                # New section that's not a date = footer
                in_footer = True
                footer_lines.append(line)
            elif in_footer:
                footer_lines.append(line)
            else:
                current_lines.append(line)

        # Save last section
        if current_date:
            sections[current_date] = current_lines
        elif current_lines and not sections:
            header_lines = current_lines

        # Separate old and recent entries
        old_dates: list[str] = []
        recent_dates: list[str] = []

        for date_str in sections.keys():
            try:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                if entry_date < cutoff_date:
                    old_dates.append(date_str)
                else:
                    recent_dates.append(date_str)
            except ValueError:
                # Invalid date format, keep it
                recent_dates.append(date_str)

        # Archive old entries by month
        if old_dates:
            archive_dir = DEFAULT_OUTPUT_DIR / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Group by month
            monthly_entries: dict[str, list[str]] = {}
            for date_str in old_dates:
                month_key = date_str[:7]  # YYYY-MM
                if month_key not in monthly_entries:
                    monthly_entries[month_key] = []
                monthly_entries[month_key].extend(sections[date_str])

            # Write archive files
            for month_key, entry_lines in monthly_entries.items():
                archive_path = archive_dir / f"MEMORY-{month_key}.md"

                # Read existing archive content
                if archive_path.exists():
                    existing = archive_path.read_text(encoding="utf-8")
                    # Merge: add new entries after header
                    if existing.strip():
                        # Find insertion point (after header, before existing content)
                        existing_lines = existing.split('\n')
                        insert_idx = 0
                        for i, l in enumerate(existing_lines):
                            if l.strip().startswith('## '):
                                insert_idx = i
                                break
                        merged = existing_lines[:insert_idx] + entry_lines + existing_lines[insert_idx:]
                        archive_content = '\n'.join(merged)
                    else:
                        archive_content = '\n'.join(entry_lines)
                else:
                    archive_content = f"# 已提取的情报项目 - {month_key} 归档\n\n" + '\n'.join(entry_lines)

                archive_path.write_text(archive_content, encoding="utf-8")
                logger.info(f"Archived {len(entry_lines)} lines to {archive_path}")

        # Build new content with only recent entries
        result_lines = header_lines.copy()

        # Sort recent dates (newest first)
        recent_dates.sort(reverse=True)
        for date_str in recent_dates:
            if date_str in sections:
                result_lines.extend(sections[date_str])

        # Add footer
        if footer_lines:
            result_lines.extend(footer_lines)

        return '\n'.join(result_lines)
