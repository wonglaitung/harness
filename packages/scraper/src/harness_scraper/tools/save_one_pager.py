"""
SaveOnePagerTool - SDK Tool for saving One-Pager Markdown files.

Generates and saves intelligence One-Pagers to the output directory.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)


class SaveOnePagerTool(Tool):
    """Save a One-Pager Markdown file with extracted intelligence."""

    @property
    def name(self) -> str:
        return "save_one_pager"

    @property
    def description(self) -> str:
        return "Save an intelligence One-Pager as a Markdown file. Generates structured content from the provided information."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
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
                "output_dir": {
                    "type": "string",
                    "description": "Output directory (default: ~/.harness/scraper)",
                },
            },
            "required": ["concept_name", "definition", "pain_point", "old_paradigm", "new_paradigm"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        concept_name = arguments["concept_name"]
        definition = arguments["definition"]
        pain_point = arguments["pain_point"]
        old_paradigm = arguments["old_paradigm"]
        new_paradigm = arguments["new_paradigm"]
        production_impact = arguments.get("production_impact", "待评估")
        adoption_cost = arguments.get("adoption_cost", "待评估")
        github_url = arguments.get("github_url", "")
        source_url = arguments.get("source_url", "")
        output_dir = arguments.get("output_dir", "~/.harness/scraper")

        try:
            # Create output directory
            output_path = Path(output_dir).expanduser()
            date_dir = output_path / datetime.now().strftime("%Y-%m-%d")
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

            logger.info(f"Saved One-Pager: {filepath}")

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