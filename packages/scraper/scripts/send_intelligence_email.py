#!/usr/bin/env python3
"""
Send daily intelligence emails.

Collects One-Pagers from ~/.harness/scraper/YYYY-MM-DD/ai/ and stocks/
and sends two separate emails:
1. AI Intelligence Daily
2. HK Stocks Alpha Daily

Usage:
    python scripts/send_intelligence_email.py
    python scripts/send_intelligence_email.py --dry-run
"""

import argparse
import logging
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

# Default output directory for One-Pagers
DEFAULT_OUTPUT_DIR = Path.home() / ".harness" / "scraper"

# HTML email style
HTML_STYLE = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; margin-top: 20px; }
    h3 { color: #7f8c8d; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th { background-color: #3498db; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    .positive { color: #27ae60; font-weight: bold; }
    .negative { color: #e74c3c; font-weight: bold; }
    .warning { color: #f39c12; }
    .info { background-color: #d5dbdb; padding: 10px; border-radius: 5px; }
    .timestamp { color: #95a5a6; font-size: 0.9em; }
    hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
</style>
"""


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def collect_markdown_files(directory: Path) -> str:
    """Collect all markdown files in a directory into a single string"""
    if not directory.exists():
        return ""

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        return ""

    contents = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        # Add horizontal rule between files
        if contents:
            contents.append("\n\n---\n\n")
        contents.append(content)

    return "".join(contents)


def markdown_to_html(md_content: str) -> str:
    """Simple Markdown to HTML conversion"""
    html = md_content

    # Convert headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Convert bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert links
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)

    # Convert lists
    lines = html.split('\n')
    in_list = False
    result_lines = []

    for line in lines:
        if line.startswith('- ') or line.startswith('* '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            result_lines.append(f'<li>{line[2:]}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)

    if in_list:
        result_lines.append('</ul>')

    html = '\n'.join(result_lines)

    # Convert tables
    if '|' in html:
        lines = html.split('\n')
        in_table = False
        result_lines = []

        for line in lines:
            if line.strip().startswith('|') and line.strip().endswith('|'):
                cells = [c.strip() for c in line.strip().split('|')[1:-1]]

                if not in_table:
                    result_lines.append('<table>')
                    in_table = True
                    result_lines.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                else:
                    if not all(c.replace('-', '').replace(':', '') == '' for c in cells):
                        result_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            else:
                if in_table:
                    result_lines.append('</table>')
                    in_table = False
                result_lines.append(line)

        if in_table:
            result_lines.append('</table>')

        html = '\n'.join(result_lines)

    # Convert paragraphs
    paragraphs = []
    current_para = []

    for line in html.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            current_para.append(stripped)
        else:
            if current_para:
                paragraphs.append('<p>' + ' '.join(current_para) + '</p>')
                current_para = []
            if stripped:
                paragraphs.append(stripped)

    if current_para:
        paragraphs.append('<p>' + ' '.join(current_para) + '</p>')

    return '\n'.join(paragraphs)


def build_html_email(title: str, content: str) -> str:
    """Build a complete HTML email"""
    html_content = markdown_to_html(content)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{title}</title>
{HTML_STYLE}
</head>
<body>
<h1>{title}</h1>
{html_content}
<p class='timestamp'>生成时间: {timestamp}</p>
</body>
</html>"""


def send_email(
    subject: str,
    content: str,
    html_content: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Send an email using SMTP"""
    # Get email config from environment
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.163.com")
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    recipients_str = os.environ.get("RECIPIENT_EMAIL", "")

    if not sender or not password or not recipients_str:
        print("⚠️ Email configuration incomplete")
        print("   Required: EMAIL_SENDER, EMAIL_PASSWORD, RECIPIENT_EMAIL")
        return False

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    if dry_run:
        print(f"[DRY RUN] Would send email: {subject}")
        print(f"  To: {recipients}")
        print(f"  Content length: {len(content)} chars")
        return True

    try:
        # Detect port and SSL
        if "163.com" in smtp_server or "qq.com" in smtp_server:
            port = 465
            use_ssl = True
        else:
            port = 587
            use_ssl = False

        # Build message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        # Add plain text
        msg.attach(MIMEText(content, "plain", "utf-8"))

        # Add HTML
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Send
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, port, timeout=30)
            server.starttls()

        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()

        print(f"✅ Email sent: {subject}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def send_daily_emails(dry_run: bool = False) -> dict:
    """Send daily intelligence emails"""
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = DEFAULT_OUTPUT_DIR / today

    results = {
        "ai_intelligence": False,
        "hk_stocks": False,
    }

    # 1. AI Intelligence Email
    ai_dir = base_dir / "ai"
    ai_content = collect_markdown_files(ai_dir)

    if ai_content:
        print(f"\n=== Sending AI Intelligence Email ===")
        print(f"Found {len(list(ai_dir.glob('*.md')))} AI One-Pagers")

        results["ai_intelligence"] = send_email(
            subject=f"AI 情报日报 - {today}",
            content=ai_content,
            html_content=build_html_email(f"AI 情报日报 - {today}", ai_content),
            dry_run=dry_run,
        )
    else:
        print(f"\n⚠️ No AI Intelligence files found in {ai_dir}")

    # 2. HK Stocks Email
    stocks_dir = base_dir / "stocks"
    stocks_content = collect_markdown_files(stocks_dir)

    if stocks_content:
        print(f"\n=== Sending HK Stocks Email ===")
        print(f"Found {len(list(stocks_dir.glob('*.md')))} Stocks One-Pagers")

        results["hk_stocks"] = send_email(
            subject=f"港股异动日报 - {today}",
            content=stocks_content,
            html_content=build_html_email(f"港股异动日报 - {today}", stocks_content),
            dry_run=dry_run,
        )
    else:
        print(f"\n⚠️ No HK Stocks files found in {stocks_dir}")

    return results


def main():
    parser = argparse.ArgumentParser(
        prog="send_intelligence_email",
        description="Send daily intelligence emails",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without actually sending",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    print(f"=== Daily Intelligence Email Sender ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Output dir: {DEFAULT_OUTPUT_DIR}")

    if args.dry_run:
        print("Mode: DRY RUN (no emails will be sent)")

    results = send_daily_emails(dry_run=args.dry_run)

    print(f"\n=== Summary ===")
    print(f"AI Intelligence: {'✅ Sent' if results['ai_intelligence'] else '❌ Not sent'}")
    print(f"HK Stocks: {'✅ Sent' if results['hk_stocks'] else '❌ Not sent'}")


if __name__ == "__main__":
    main()
