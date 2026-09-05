"""
Result Sanitizer - Sanitize sensitive information from outputs.

Removes API keys, passwords, emails, and other sensitive data from tool outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern
from typing import Any


@dataclass
class SanitizationRule:
    """
    Sanitization rule.

    Defines a pattern to detect and replacement to apply.
    """

    name: str
    pattern: Pattern
    replacement: str
    description: str = ""


class ResultSanitizer:
    """
    Result sanitizer.

    Removes sensitive information from tool outputs before
    returning to the LLM.
    """

    DEFAULT_RULES = [
        SanitizationRule(
            name="api_key",
            pattern=re.compile(r'(api[_-]?key["\s:=]+)["\']?[\w-]{20,}["\']?', re.I),
            replacement=r"\1[REDACTED]",
            description="API Key",
        ),
        SanitizationRule(
            name="password",
            pattern=re.compile(r'(password["\s:=]+)["\']?[^\s"\']{8,}["\']?', re.I),
            replacement=r"\1[REDACTED]",
            description="Password",
        ),
        SanitizationRule(
            name="aws_key",
            pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
            replacement="AKIA[REDACTED]",
            description="AWS Access Key",
        ),
        SanitizationRule(
            name="secret_key",
            pattern=re.compile(r'(secret[_-]?key["\s:=]+)["\']?[\w-]{20,}["\']?', re.I),
            replacement=r"\1[REDACTED]",
            description="Secret Key",
        ),
        SanitizationRule(
            name="token",
            pattern=re.compile(r'(token["\s:=]+)["\']?[\w-]{20,}["\']?', re.I),
            replacement=r"\1[REDACTED]",
            description="Token",
        ),
        SanitizationRule(
            name="private_key",
            pattern=re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
            replacement="-----BEGIN PRIVATE KEY [REDACTED]-----",
            description="Private Key",
        ),
        SanitizationRule(
            name="email",
            pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            replacement="[EMAIL REDACTED]",
            description="Email Address",
        ),
        SanitizationRule(
            name="credit_card",
            pattern=re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            replacement="[CARD REDACTED]",
            description="Credit Card",
        ),
        SanitizationRule(
            name="phone",
            pattern=re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
            replacement="[PHONE REDACTED]",
            description="Phone Number",
        ),
        SanitizationRule(
            name="ssn",
            pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            replacement="[SSN REDACTED]",
            description="Social Security Number",
        ),
    ]

    def __init__(
        self,
        rules: list[SanitizationRule] | None = None,
        max_length: int = 100_000,
        enabled: bool = True,
    ):
        """
        Initialize sanitizer.

        Args:
            rules: Sanitization rules (default rules if None)
            max_length: Maximum output length
            enabled: Whether sanitization is enabled
        """
        self.rules = rules or self.DEFAULT_RULES.copy()
        self.max_length = max_length
        self.enabled = enabled

    def sanitize(self, content: str) -> str:
        """
        Sanitize content.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content
        """
        if not self.enabled:
            return content

        result = content

        # Apply all rules
        for rule in self.rules:
            result = rule.pattern.sub(rule.replacement, result)

        # Truncate if too long
        if len(result) > self.max_length:
            head = result[: self.max_length // 2]
            tail = result[-self.max_length // 4 :]
            result = f"{head}\n\n... [截断] ...\n\n{tail}"

        return result

    def get_redaction_report(self, original: str) -> dict[str, Any]:
        """
        Get report of what was redacted.

        Args:
            original: Original content

        Returns:
            Redaction report
        """
        report: dict[str, Any] = {"redactions": []}

        for rule in self.rules:
            matches = rule.pattern.findall(original)
            if matches:
                count = len(matches) if isinstance(matches, list) else 1
                report["redactions"].append(
                    {
                        "rule": rule.name,
                        "description": rule.description,
                        "count": count,
                    }
                )

        report["total_redactions"] = sum(r["count"] for r in report["redactions"])

        return report

    def add_rule(self, rule: SanitizationRule) -> None:
        """
        Add a custom rule.

        Args:
            rule: Rule to add
        """
        self.rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """
        Remove a rule by name.

        Args:
            name: Rule name

        Returns:
            True if rule was removed
        """
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                return True
        return False

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize dictionary values.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.sanitize(value)
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize(item) if isinstance(item, str) else item for item in value
                ]
            else:
                result[key] = value
        return result


def sanitize_output(content: str, max_length: int = 100_000) -> str:
    """
    Quick sanitize function.

    Args:
        content: Content to sanitize
        max_length: Maximum length

    Returns:
        Sanitized content
    """
    sanitizer = ResultSanitizer(max_length=max_length)
    return sanitizer.sanitize(content)
