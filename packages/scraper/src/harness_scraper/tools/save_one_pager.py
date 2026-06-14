"""
SaveOnePagerTool - SDK Tool for saving One-Pager Markdown files.

Generates and saves intelligence One-Pagers to the output directory.
Automatically updates MEMORY.md to track processed items.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Default output directory: packages/scraper/output/
# save_one_pager.py is in packages/scraper/src/harness_scraper/tools/
# Need to go up 4 levels: tools -> harness_scraper -> src -> scraper -> output
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"
MEMORY_PATH = DEFAULT_OUTPUT_DIR / "MEMORY.md"


class SaveOnePagerTool(Tool):
    """Save a One-Pager Markdown file with extracted intelligence."""

    @property
    def name(self) -> str:
        return "save_one_pager"

    @property
    def description(self) -> str:
        return "Save an intelligence One-Pager as a Markdown file. IMPORTANT: Use domain='stocks' for stock/financial content (港股, buybacks, financial news), domain='ai' for AI/tech content."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                # Simple mode (direct content)
                "title": {
                    "type": "string",
                    "description": "Title for the One-Pager (simple mode)",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content to save (simple mode)",
                },
                "filename": {
                    "type": "string",
                    "description": "Filename for the output file (simple mode, optional)",
                },
                # Structured mode (AI intelligence)
                "concept_name": {
                    "type": "string",
                    "description": "Name of the concept/tool/technology",
                },
                "definition": {
                    "type": "string",
                    "description": "Technical definition in plain language",
                },
                "pain_point": {
                    "type": "string",
                    "description": "What problem does it solve",
                },
                "old_paradigm": {
                    "type": "string",
                    "description": "How things were done before",
                },
                "new_paradigm": {
                    "type": "string",
                    "description": "How things are done now with this",
                },
                "production_impact": {
                    "type": "string",
                    "description": "Impact on developer productivity",
                },
                "adoption_cost": {
                    "type": "string",
                    "description": "Cost to adopt (time, money, effort)",
                },
                "github_url": {
                    "type": "string",
                    "description": "GitHub repository URL",
                },
                "source_url": {
                    "type": "string",
                    "description": "Original source URL where discovered",
                },
                "domain": {
                    "type": "string",
                    "enum": ["ai", "stocks"],
                    "description": "Output domain: 'ai' for AI intelligence, 'stocks' for stock analysis",
                },
            },
            # Either (title + content) or (concept_name + definition + ...) required
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        domain = arguments.get("domain", "ai")

        # Determine mode: simple (title + content) or structured (concept_name + ...)
        if "title" in arguments and "content" in arguments:
            # Simple mode
            return await self._execute_simple(arguments, domain)
        elif "concept_name" in arguments:
            # Structured mode (AI intelligence)
            return await self._execute_structured(arguments, domain)
        else:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Either (title + content) or (concept_name + definition + ...) required",
            )

    async def _execute_simple(
        self,
        arguments: dict[str, Any],
        domain: str,
    ) -> ToolResult:
        """Simple mode: save title + content directly."""
        title = arguments["title"]
        content = arguments["content"]
        filename = arguments.get("filename", "")

        try:
            # Create output directory with domain subdirectory
            output_path = DEFAULT_OUTPUT_DIR
            date_dir = output_path / datetime.now().strftime("%Y-%m-%d") / domain
            date_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            if not filename:
                filename = self._to_filename(title) + ".md"
            elif not filename.endswith(".md"):
                filename = filename + ".md"

            filepath = date_dir / filename

            # Write content directly
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Saved One-Pager (simple): {filepath}")

            # Update MEMORY.md
            self._update_memory(title, domain, arguments.get("source_url", ""))

            return ToolResult(
                tool_call_id="",
                success=True,
                content=f"One-Pager saved to: {filepath}\n\nPreview:\n{content[:500]}...",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to save One-Pager: {str(e)}",
            )

    async def _execute_structured(
        self,
        arguments: dict[str, Any],
        domain: str,
    ) -> ToolResult:
        """Structured mode: generate AI intelligence One-Pager."""
        concept_name = arguments["concept_name"]
        definition = arguments.get("definition", "")
        pain_point = arguments.get("pain_point", "")
        old_paradigm = arguments.get("old_paradigm", "")
        new_paradigm = arguments.get("new_paradigm", "")
        production_impact = arguments.get("production_impact", "待评估")
        adoption_cost = arguments.get("adoption_cost", "待评估")
        github_url = arguments.get("github_url", "")
        source_url = arguments.get("source_url", "")

        try:
            # Create output directory with domain subdirectory
            output_path = DEFAULT_OUTPUT_DIR
            date_dir = output_path / datetime.now().strftime("%Y-%m-%d") / domain
            date_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from concept name
            filename = self._to_filename(concept_name)
            filepath = date_dir / f"{filename}.md"

            # Generate Markdown content
            markdown = self._generate_markdown(
                concept_name=concept_name,
                definition=definition,
                pain_point=pain_point,
                old_paradigm=old_paradigm,
                new_paradigm=new_paradigm,
                production_impact=production_impact,
                adoption_cost=adoption_cost,
                github_url=github_url,
                source_url=source_url,
            )

            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            logger.info(f"Saved One-Pager (structured): {filepath}")

            # Update MEMORY.md
            self._update_memory(concept_name, domain, source_url or github_url)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=f"One-Pager saved to: {filepath}\n\nPreview:\n{markdown[:500]}...",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to save One-Pager: {str(e)}",
            )

    def _to_filename(self, name: str) -> str:
        """Convert concept name to valid filename."""
        # Remove special characters
        name = re.sub(r"[^\w\s\-]", "", name)
        # Replace spaces with hyphens
        name = re.sub(r"\s+", "-", name)
        # Lowercase
        name = name.lower()
        # Limit length
        return name[:50]

    def _generate_markdown(
        self,
        concept_name: str,
        definition: str,
        pain_point: str,
        old_paradigm: str,
        new_paradigm: str,
        production_impact: str,
        adoption_cost: str,
        github_url: str,
        source_url: str,
    ) -> str:
        """Generate One-Pager Markdown content."""
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"""# {concept_name}

## 技术定义 (What)
{definition}

## 行业痛点 (Why)
{pain_point}

## 旧范式 vs 新范式
- **旧做法**：{old_paradigm}
- **新做法**：{new_paradigm}

## 生产力影响 (How)
{production_impact}

## 采用成本
{adoption_cost}

## 核心线索
- GitHub：{github_url}
- 来源：{source_url}
- 发布时间：{date_str}
"""

    def _update_memory(self, name: str, domain: str, source_url: str) -> None:
        """
        Update MEMORY.md with the saved item.

        Args:
            name: Item name (title or concept_name)
            domain: "ai" or "stocks"
            source_url: Source URL
        """
        try:
            # Determine category based on domain
            if domain == "stocks":
                category = "港股分析"
            else:
                category = "新范式/工具"

            # Load or create MEMORY.md
            MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

            if MEMORY_PATH.exists():
                content = MEMORY_PATH.read_text(encoding="utf-8")
            else:
                content = self._create_initial_memory()

            # Add entry
            date_str = datetime.now().strftime("%Y-%m-%d")
            content = self._add_memory_entry(content, name, category, source_url, date_str)

            # Write back
            MEMORY_PATH.write_text(content, encoding="utf-8")
            logger.debug(f"Updated MEMORY.md with: {name}")

        except Exception as e:
            logger.warning(f"Failed to update MEMORY.md: {e}")

    def _create_initial_memory(self) -> str:
        """Create initial MEMORY.md content."""
        return """# 已提取的情报项目

记录已处理的 AI 项目和港股分析，避免重复抓取。

## 注意事项

- 成熟项目（vLLM、LangChain、Ollama 等）已通过技能文件排除
- 新范式项目优先级：概念 > 架构 > 工具
- 定期审查，移除已成熟的项目

"""

    def _add_memory_entry(self, content: str, name: str, category: str, source_url: str, date_str: str) -> str:
        """Add an entry to MEMORY.md content."""
        date_header = f"## {date_str} 提取"

        # Check if date section exists
        if date_header not in content:
            # Add new date section before 注意事项
            if "## 注意事项" in content:
                content = content.replace("## 注意事项", f"{date_header}\n\n## 注意事项")
            else:
                content = content.rstrip() + f"\n\n{date_header}\n"

        # Build entry line
        if source_url:
            entry_line = f"- **{name}** - {source_url}"
        else:
            entry_line = f"- **{name}**"

        # Check if entry already exists
        if entry_line in content:
            return content

        # Find the date section and add entry
        lines = content.split("\n")
        result_lines = []
        in_date_section = False
        in_category_section = False
        category_header = f"### {category}"
        inserted = False

        for i, line in enumerate(lines):
            result_lines.append(line)

            if line.strip() == date_header:
                in_date_section = True
            elif in_date_section and line.strip().startswith("## "):
                # End of date section
                if not inserted:
                    # Add category and entry
                    result_lines.append(f"\n{category_header}")
                    result_lines.append(entry_line)
                    inserted = True
                in_date_section = False
            elif in_date_section and line.strip() == category_header:
                in_category_section = True
            elif in_category_section and line.strip().startswith("### "):
                # End of category section
                if not inserted:
                    result_lines.append(entry_line)
                    inserted = True
                in_category_section = False

        # If not inserted, add at the end of date section
        if not inserted:
            # Find position after date header
            for i, line in enumerate(result_lines):
                if line.strip() == date_header:
                    # Insert category and entry after date header
                    result_lines.insert(i + 1, f"\n{category_header}")
                    result_lines.insert(i + 2, entry_line)
                    break

        return "\n".join(result_lines)