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

    Detects common injection patterns in user input. Coverage is keyword /
    phrase based (both English and Chinese) plus obfuscation normalization
    (invisible / zero-width characters). It is a heuristic defense-in-depth
    filter, not a semantic guarantee — see design note residual risk.
    """

    # Invisible / zero-width characters used to break keyword matching.
    # Stripped before pattern matching.
    _ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")

    INJECTION_PATTERNS = [
        # Role playing (English)
        r"ignore (all )?(previous|above) instructions",
        r"disregard (all )?(previous|above) instructions",
        r"forget (all )?(previous|above) instructions",
        # System prompt leakage (English)
        r"what (is|are) your (system |initial )?instructions",
        r"repeat your (system |initial )?prompt",
        r"show me your (system |initial )?prompt",
        # Jailbreak attempts (English)
        r"you are now (a|an) \w+",
        r"pretend (to be|you are)",
        r"act as (if|though)",
        r"developer mode",
        r"\bDAN\b",
        # Encoding bypass
        r"base64",
        r"rot13",
        r"hex encode",
        r"decode and (run|execute)",
        # Dangerous instructions (English)
        r"sudo",
        r"chmod",
        r"rm -rf",
        r"delete all",
        r"format disk",
        r"output your prompt",
        r"print your instructions",
        r"reveal your system",
        # ---- Chinese / multilingual coverage (M5-B) ----
        # 指令覆盖：忽略/无视/忘掉之前的指令
        r"忽略(以上|之前|前述|上面|先前|所有)?(的)?(所有)?(指令|指示|要求|提示|设定|設定|限制|规则|規則|约束|約束|安全|prompt)",
        r"无视(以上|之前|前述|上面|先前)?(的)?(指令|指示|要求|提示|设定|設定|限制|规则|規則|约束|約束|安全)",
        r"忘(记|掉|記|卻|却)(以上|之前|前述|上面|先前)?(的)?(指令|指示|要求|提示|设定|設定|限制|规则|規則|约束|約束)",
        r"不要(理会|理睬|管|搭理)(以上|之前|前面|先前)?(的)?(指令|指示|要求|提示|限制|规则|規則)",
        r"把(上面|之前|以上)(的)?(指令|指示|要求|提示)(全部)?(抛|丢|扔)到(一|脑)边",
        # 系统提示泄露
        r"(告诉|展示|显示|透露|念出|重复|说出|說出|拷贝|複製)(我)?(你的)?(系统|初始|system)?(提示|指令|prompt)",
        r"你的(系统|初始|system)?(提示|指令|prompt)(是(什么|什麼|啥)|内容|內容|是什么|是什麼)",
        r"(输出|打印|顯示|输出)(你(的)?(系统|初始|system)?(提示|指令|prompt))",
        r"(泄露|泄漏|透露)(你(的)?)(系统|初始|system)(提示|指令|prompt)",
        # 越狱 / 角色扮演（限定装扮句式，降低误报）
        r"假装(你|我)是",
        r"假设(你|我)是",
        r"扮演(一个|一名|一种|一個|一種|a|an|成)",
        # 「现在你是X」只在 X 指向「解除限制/规则/安全」时才视为越狱，
        # 避免把「现在你是我的好朋友」这类正常表述误报。
        r"(现在|現在)你(就)?(是|变成|變成).{0,10}(限制|约束|約束|规则|規則|安全)",
        r"越(狱|獄)",
        # 危险指令（中文）
        r"删除(所有|全部|一切|全部)?(的)?(文件|数据|資料|记录|記錄|资料)",
        r"格式化(磁盘|硬盘|磁碟|硬碟|系统|系統)",
        r"(运行|执行|執行)(以下|下列|这个|這個|恶意|惡意)?(的)?(命令|指令|脚本|腳本)",
        r"(解密|解碼|解码)(后|後)(运行|执行|執行)",
    ]

    @staticmethod
    def _normalize(text: str) -> str:
        # Strip invisible characters (zero-width spaces, soft hyphen, BOM,
        # word joiner) that attackers insert to defeat substring/keyword
        # matching, e.g. "ign\u200bore".
        return PromptInjectionDetector._ZERO_WIDTH.sub("", text)

    def __init__(self, custom_patterns: list[str] | None = None):
        """
        Initialize detector.

        Args:
            custom_patterns: Additional patterns to detect
        """
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        if custom_patterns:
            self.patterns.extend(re.compile(p, re.IGNORECASE) for p in custom_patterns)

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

        # Normalize away invisible characters before pattern matching (M5-B).
        text = self._normalize(text)

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
                    sanitized_text = self._normalize(block.get("text", ""))
                    for pattern in self.patterns:
                        sanitized_text = pattern.sub("[FILTERED]", sanitized_text)
                    sanitized_list.append({"type": "text", "text": sanitized_text})
                else:
                    # Keep non-text blocks unchanged
                    sanitized_list.append(block)
            return sanitized_list

        # String input
        sanitized = self._normalize(text)
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
        block_injection: bool = True,
    ):
        """
        Initialize validator.

        Args:
            max_length: Maximum input length
            check_injection: Whether to check for injection patterns
            custom_patterns: Custom injection patterns
            block_injection: When True, detected injection is a hard error (input is
                rejected). When False, it is only a warning and the sanitized text
                can still be used.
        """
        self.max_length = max_length
        self.block_injection = block_injection
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
                # B1: external/tool input that tries to hijack the agent must be a
                # hard failure by default, not just an advisory warning.
                if self.block_injection:
                    errors.append(f"Potential injection patterns detected: {patterns}")
                else:
                    warnings.append(f"Potential injection patterns detected: {patterns}")

        # Sanitize text
        sanitized = self.injection_detector.sanitize(text) if self.injection_detector else text

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
            sanitized_text=content
            if isinstance(content, str)
            else content.decode("utf-8", errors="replace"),
        )
