"""
Permission management for tool execution.
"""

from dataclasses import dataclass, field
from pathlib import Path


def get_harness_config_dir() -> Path:
    """Get the harness config directory (~/.harness)."""
    return Path.home() / ".harness"


@dataclass
class PermissionSet:
    """
    Defines permissions for tool execution.

    Controls what paths, commands, and networks tools can access.
    """

    # Path permissions
    allowed_read_paths: set[Path] = field(default_factory=set)
    allowed_write_paths: set[Path] = field(default_factory=set)

    # Command permissions
    allowed_commands: set[str] = field(default_factory=set)
    blocked_commands: set[str] = field(default_factory=set)

    # Network permissions
    allowed_hosts: set[str] = field(default_factory=set)
    network_enabled: bool = False

    @classmethod
    def full_access(cls) -> "PermissionSet":
        """Create a permission set with full access."""
        return cls(
            network_enabled=True,
        )

    @classmethod
    def read_only(cls, paths: list[str] | None = None) -> "PermissionSet":
        """Create a read-only permission set."""
        perm = cls()
        if paths:
            for p in paths:
                perm.allowed_read_paths.add(Path(p))
        return perm

    @classmethod
    def sandbox(
        cls,
        workspace: str,
        allow_network: bool = False,
    ) -> "PermissionSet":
        """
        Create a sandboxed permission set.

        Args:
            workspace: Base directory for file operations
            allow_network: Whether to allow network access

        The sandbox allows access to:
        - The workspace directory (read/write)
        - ~/.harness/ directory (read only for skills/configs)
        - System temp directory (read/write for temporary files)
        """
        workspace_path = Path(workspace).resolve()
        harness_dir = get_harness_config_dir()

        # Get system temp directory
        import tempfile
        temp_dir = Path(tempfile.gettempdir())

        return cls(
            allowed_read_paths={workspace_path, harness_dir, temp_dir},
            allowed_write_paths={workspace_path, temp_dir},
            network_enabled=allow_network,
        )

    def is_path_allowed(self, path: str, mode: str = "read") -> bool:
        """
        Check if a path is accessible.

        Args:
            path: Path to check
            mode: "read" or "write"

        Returns:
            True if access is allowed
        """
        # Get the appropriate permission set based on mode
        allowed = self.allowed_read_paths if mode == "read" else self.allowed_write_paths

        # For write mode, if no write paths specified, deny by default
        # (unless read paths are also empty, meaning full access)
        if mode == "write" and not allowed and not self.allowed_read_paths:
            return True  # Full access mode
        if mode == "write" and not allowed:
            return False  # Read-only mode - no write paths allowed

        # For read mode, if no read paths specified, allow all
        if mode == "read" and not allowed:
            return True

        try:
            check_path = Path(path).resolve()
        except (OSError, ValueError):
            return False

        for allowed_path in allowed:
            try:
                check_path.relative_to(allowed_path)
                return True
            except ValueError:
                continue

        return False

    def is_command_allowed(self, command: str) -> bool:
        """
        Check if a command is allowed.

        Args:
            command: Command to check

        Returns:
            True if command is allowed
        """
        # Check blocked first
        base_cmd = command.split()[0] if command else ""
        if base_cmd in self.blocked_commands:
            return False

        # If no allowed commands specified, allow all non-blocked
        if not self.allowed_commands:
            return True

        return base_cmd in self.allowed_commands

    def is_host_allowed(self, host: str) -> bool:
        """Check if a host is accessible."""
        if not self.network_enabled:
            return False

        if not self.allowed_hosts:
            return True

        return host in self.allowed_hosts

    def merge(self, other: "PermissionSet") -> "PermissionSet":
        """
        Merge with another permission set.

        Returns a new PermissionSet with combined permissions.
        """
        return PermissionSet(
            allowed_read_paths=self.allowed_read_paths | other.allowed_read_paths,
            allowed_write_paths=self.allowed_write_paths | other.allowed_write_paths,
            allowed_commands=self.allowed_commands | other.allowed_commands,
            blocked_commands=self.blocked_commands | other.blocked_commands,
            allowed_hosts=self.allowed_hosts | other.allowed_hosts,
            network_enabled=self.network_enabled or other.network_enabled,
        )
