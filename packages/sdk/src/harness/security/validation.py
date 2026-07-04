"""
Input Validation - Validate and sanitize user inputs.

Provides prompt injection detection and input validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """
    Result of input validation.

    Contains validity status, errors, warnings, and sanitized text.
    """

    valid: bool
    errors: list[str]
    warnings: list[str]
    sanitized_text: str


class PromptInjectionDetector:
    """
    Prompt injection detector.

    Detects common injection patterns in user input.
    """

    INJECTION_PATTERNS = [
        # Role playing
        r"ignore (all )?(previous|above) instructions",
        r"disregard (all )?(previous|above) instructions",
        r"forget (all )?(previous|above) instructions",
        # System prompt leakage
        r"what (is|are) your (system |initial )?instructions",
        r"repeat your (system |initial )?prompt",
        r"show me your (system |initial )?prompt",
        # Jailbreak attempts
        r"you are now (a|an) \w+",
        r"pretend (to be|you are)",
        r"act as (if|though)",
        # Encoding bypass
        r"base64",
        r"rot13",
        r"hex encode",
        # Dangerous instructions
        r"sudo",
        r"chmod",
        r"rm -rf",
        r"delete all",
        r"format disk",
        # Output manipulation
        r"output your prompt",
        r"print your instructions",
        r"reveal your system",
    ]

    def __init__(self, custom_patterns: list[str] | None = None):
        """
        Initialize detector.

        Args:
            custom_patterns: Additional patterns to detect
        """
        self.patterns = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
        ]
        if custom_patterns:
            self.patterns.extend(
                re.compile(p, re.IGNORECASE) for p in custom_patterns
            )

    def detect(self, text: str | list[dict[str, Any]]) -> tuple[bool, list[str]]:
        """
        Detect injection attempts.

        Args:
            text: Text to analyze - can be a string or multimodal content list

        Returns:
            (is_safe, detected_patterns) tuple
        """
        # Handle multimodal content (list of dicts)
        if isinstance(text, list):
            text_content = ""
            for block in text:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
            text = text_content

        if not text or not isinstance(text, str):
            return True, []  # Safe if no text content

        detected = []

        for pattern in self.patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)

        return len(detected) == 0, detected

    def sanitize(self, text: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
        """
        Sanitize text by escaping special patterns.

        Note: Sanitization doesn't guarantee safety. Consider
        rejecting inputs with detected patterns instead.

        Args:
            text: Text to sanitize - can be a string or multimodal content list

        Returns:
            Sanitized text (same type as input)
        """
        # Handle multimodal content (list of dicts)
        if isinstance(text, list):
            sanitized_list = []
            for block in text:
                if isinstance(block, dict) and block.get("type") == "text":
                    # Sanitize text blocks
                    sanitized_text = block.get("text", "")
                    for pattern in self.patterns:
                        sanitized_text = pattern.sub("[FILTERED]", sanitized_text)
                    sanitized_list.append({"type": "text", "text": sanitized_text})
                else:
                    # Keep non-text blocks unchanged
                    sanitized_list.append(block)
            return sanitized_list

        # String input
        sanitized = text
        for pattern in self.patterns:
            sanitized = pattern.sub("[FILTERED]", sanitized)

        return sanitized


class InputValidator:
    """
    Input validator.

    Validates input length and checks for injection patterns.
    """

    def __init__(
        self,
        max_length: int = 100000,
        check_injection: bool = True,
        custom_patterns: list[str] | None = None,
    ):
        """
        Initialize validator.

        Args:
            max_length: Maximum input length
            check_injection: Whether to check for injection patterns
            custom_patterns: Custom injection patterns
        """
        self.max_length = max_length
        self.injection_detector = (
            PromptInjectionDetector(custom_patterns) if check_injection else None
        )

    def validate(self, text: str | list[dict[str, Any]]) -> ValidationResult:
        """
        Validate input.

        Args:
            text: Input to validate - can be a string or multimodal content list

        Returns:
            ValidationResult
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Extract text content for length check
        text_content = text
        if isinstance(text, list):
            text_content = ""
            for block in text:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")

        # Length check
        if isinstance(text_content, str) and len(text_content) > self.max_length:
            errors.append(f"Input exceeds maximum length ({self.max_length})")

        # Injection detection
        if self.injection_detector:
            is_safe, patterns = self.injection_detector.detect(text)
            if not is_safe:
                warnings.append(f"Potential injection patterns detected: {patterns}")

        # Sanitize text
        sanitized = (
            self.injection_detector.sanitize(text)
            if self.injection_detector
            else text
        )

        # For ValidationResult, convert list back to string representation
        sanitized_text = sanitized if isinstance(sanitized, str) else str(sanitized)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_text=sanitized_text,
        )

    def is_safe(self, text: str | list[dict[str, Any]]) -> bool:
        """
        Quick check if input is safe.

        Args:
            text: Input to check - can be a string or multimodal content list

        Returns:
            True if input passes all checks
        """
        result = self.validate(text)
        return result.valid and len(result.warnings) == 0


class FileInputValidator:
    """
    Validator for file-related inputs.

    Validates file paths and content.
    """

    DANGEROUS_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".sh",
        ".ps1",
        ".vbs",
        ".js",
        ".jar",
    }

    DANGEROUS_PATHS = {
        "/etc/passwd",
        "/etc/shadow",
        "/root/.ssh",
        "~/.ssh",
        "~/.aws",
        "~/.gnupg",
    }

    def __init__(
        self,
        allowed_extensions: set[str] | None = None,
        blocked_extensions: set[str] | None = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        """
        Initialize file validator.

        Args:
            allowed_extensions: Allowed file extensions
            blocked_extensions: Blocked file extensions
            max_file_size: Maximum file size
        """
        self.allowed_extensions = allowed_extensions
        self.blocked_extensions = blocked_extensions or self.DANGEROUS_EXTENSIONS
        self.max_file_size = max_file_size

    def validate_path(self, path: str) -> ValidationResult:
        """
        Validate file path.

        Args:
            path: File path to validate

        Returns:
            ValidationResult
        """
        errors: list[str] = []
        warnings: list[str] = []

        import os

        # Expand path
        expanded = os.path.expanduser(path)

        # Check dangerous paths
        for dangerous in self.DANGEROUS_PATHS:
            if dangerous in expanded:
                errors.append(f"Access to sensitive path denied: {dangerous}")

        # Check extension
        _, ext = os.path.splitext(path)
        ext = ext.lower()

        if self.blocked_extensions and ext in self.blocked_extensions:
            errors.append(f"File extension not allowed: {ext}")

        if self.allowed_extensions and ext not in self.allowed_extensions:
            errors.append(f"File extension not in allowed list: {ext}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_text=expanded,
        )

    def validate_content(self, content: str | bytes) -> ValidationResult:
        """
        Validate file content.

        Args:
            content: File content to validate

        Returns:
            ValidationResult
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Size check
        size = len(content) if isinstance(content, bytes) else len(content.encode())
        if size > self.max_file_size:
            errors.append(f"File size ({size}) exceeds maximum ({self.max_file_size})")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_text=content if isinstance(content, str) else content.decode("utf-8", errors="replace"),
        )
