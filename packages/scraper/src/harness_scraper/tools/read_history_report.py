"""
ReadHistoryReportTool - SDK Tool for reading historical One-Pager reports.

Supports querying historical reports by:
- Date range (e.g., last 7 days)
- Keywords (stock names, event types)
- Domain (stocks or ai)

Use case: When current data references past events (e.g., "continuous inflow for 3 days",
"verifying earlier signals"), this tool helps find and read related historical reports.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Default output directory: packages/scraper/output/
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"


class ReadHistoryReportTool(Tool):
    """Read historical One-Pager reports for trend analysis."""

    @property
    def name(self) -> str:
        return "read_history_report"

    @property
    def description(self) -> str:
        return (
            "Read historical One-Pager reports for trend analysis. "
            "Use when current data references past events "
            "(e.g., 'continuous inflow for 3 days', 'verifying earlier signals'). "
            "Returns matching reports with their content, date, and file path."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of past days to search (default: 7, max: 30)",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to filter reports (stock names, event types). "
                    "If empty, returns all reports in the date range.",
                },
                "domain": {
                    "type": "string",
                    "enum": ["stocks", "ai"],
                    "description": "Report domain (default: stocks)",
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        days = min(arguments.get("days", 7), 30)  # Cap at 30 days
        keywords = arguments.get("keywords", [])
        domain = arguments.get("domain", "stocks")

        try:
            # Calculate date range
            today = datetime.now().date()
            start_date = today - timedelta(days=days)

            # Collect matching reports
            reports: list[dict[str, str]] = []

            for i in range(days):
                date = today - timedelta(days=i)
                date_dir = DEFAULT_OUTPUT_DIR / date.strftime("%Y-%m-%d") / domain

                if not date_dir.exists():
                    continue

                # Read all .md files in the directory
                for md_file in sorted(date_dir.glob("*.md")):
                    # Filter by keywords if provided
                    if keywords:
                        filename = md_file.stem
                        if not any(kw.lower() in filename.lower() for kw in keywords):
                            continue

                    # Read file content
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        reports.append({
                            "date": date.strftime("%Y-%m-%d"),
                            "filename": md_file.stem,
                            "path": str(md_file),
                            "content": content,
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read {md_file}: {e}")
                        continue

            # Build result
            if reports:
                # Format reports for output
                result_parts = [f"Found {len(reports)} historical report(s):\n"]

                for report in reports:
                    result_parts.append(f"---\n")
                    result_parts.append(f"**Date**: {report['date']}\n")
                    result_parts.append(f"**File**: {report['filename']}\n")
                    result_parts.append(f"**Path**: {report['path']}\n")
                    result_parts.append(f"\n**Content**:\n{report['content']}\n")

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content="\n".join(result_parts),
                )
            else:
                # No reports found
                search_info = [
                    "未找到匹配的历史报告。",
                    f"搜索条件：days={days}, keywords={keywords}",
                    f"已搜索目录：{start_date} 至 {today}",
                    "",
                    "建议：将当前信息作为首次记录，建立跟踪基线。",
                ]

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content="\n".join(search_info),
                )

        except Exception as e:
            logger.error(f"Failed to read history reports: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to read history reports: {str(e)}",
            )
