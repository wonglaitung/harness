"""
GitHub connector for GitHub App integration.

This module provides GitHubConnector for receiving GitHub webhook events
and interacting with GitHub API (creating comments, updating PRs, etc.).
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from harness.connectors.base import Connector, EventCallback
from harness.connectors.types import (
    ConnectorEvent,
    ConnectorState,
    ConnectorType,
    GitHubConfig,
    RoutingKeys,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GitHubConnector(Connector):
    """
    GitHub connector for GitHub App integration.

    Features:
    - Receive GitHub webhook events
    - Create PR/Issue comments
    - Extract routing metadata for PR/Issue context

    Usage:
        ```python
        github = GitHubConnector(
            config=GitHubConfig(
                app_id="123456",
                private_key="-----BEGIN RSA PRIVATE KEY-----\\n...",
                webhook_secret="whsec_...",
            )
        )
        await github.start(event_callback)

        # Handle webhook
        await github.handle_webhook("pull_request", payload)

        # Create PR comment
        await github.create_pr_comment(
            repo="owner/repo",
            pr_number=42,
            body="Review complete!",
        )
        ```
    """

    connector_type = ConnectorType.GITHUB

    def __init__(
        self,
        config: GitHubConfig,
        connector_id: str = "",
    ):
        """
        Initialize GitHubConnector.

        Args:
            config: GitHub configuration
            connector_id: Optional connector ID
        """
        self.config = config
        self.id = connector_id or self._generate_id()
        self._callback: EventCallback | None = None
        self._gh: Any = None  # GitHub API client
        self.state = ConnectorState.IDLE

    async def start(self, event_callback: EventCallback) -> None:
        """
        Start the GitHub connector.

        Args:
            event_callback: Async callback for events
        """
        self._callback = event_callback

        try:
            # Initialize GitHub API client
            # Using gidgethub or PyGithub
            self._gh = _GitHubAPIClient(
                app_id=self.config.app_id,
                private_key=self.config.private_key,
            )

            self.state = ConnectorState.RUNNING
            logger.info(f"GitHubConnector started: {self.id}")

        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.state = ConnectorState.ERROR
            raise

    async def handle_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Handle a GitHub webhook event.

        Called by WebhookConnector when a GitHub webhook is received.

        Args:
            event_type: GitHub event type (e.g., "push", "pull_request")
            payload: Webhook payload
        """
        # Check if we should handle this event
        if event_type not in self.config.events:
            return

        # Extract routing metadata
        routing_metadata = self._extract_routing_metadata(event_type, payload)

        # Get repository name
        repo = payload.get("repository", {})
        source = repo.get("full_name", "unknown")

        # Create event
        connector_event = self.create_event(
            event_type=f"github.{event_type}",
            payload=payload,
            source=source,
            routing_metadata=routing_metadata,
        )

        # Async callback
        if self._callback:
            await self._callback(connector_event)

    def _extract_routing_metadata(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract routing metadata from GitHub payload.

        Enables "reply to PR" functionality.
        """
        metadata = {}

        # Pull request events
        if event_type == "pull_request" and "pull_request" in payload:
            pr = payload["pull_request"]
            metadata[RoutingKeys.GITHUB_PR_NUMBER] = pr.get("number")

        # Issue events
        elif event_type in ("issues", "issue_comment") and "issue" in payload:
            issue = payload["issue"]
            metadata[RoutingKeys.GITHUB_ISSUE_NUMBER] = issue.get("number")

        # Repository info
        repo = payload.get("repository", {})
        if repo.get("full_name"):
            metadata[RoutingKeys.GITHUB_REPO] = repo.get("full_name")

        # User info
        sender = payload.get("sender", {})
        if sender.get("login"):
            metadata[RoutingKeys.USER_ID] = sender.get("login")

        return metadata

    async def create_pr_comment(
        self,
        repo: str,
        pr_number: int,
        body: str,
    ) -> bool:
        """
        Create a comment on a pull request.

        Args:
            repo: Repository name (owner/repo)
            pr_number: PR number
            body: Comment body

        Returns:
            True if successful
        """
        if not self._gh:
            logger.warning("GitHub client not initialized")
            return False

        try:
            await self._gh.create_issue_comment(repo, pr_number, body)
            logger.info(f"Created PR comment on {repo}#{pr_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to create PR comment: {e}")
            return False

    async def create_issue_comment(
        self,
        repo: str,
        issue_number: int,
        body: str,
    ) -> bool:
        """
        Create a comment on an issue.

        Args:
            repo: Repository name (owner/repo)
            issue_number: Issue number
            body: Comment body

        Returns:
            True if successful
        """
        # Issues and PRs share the same API
        return await self.create_pr_comment(repo, issue_number, body)

    async def get_pr(self, repo: str, pr_number: int) -> dict[str, Any] | None:
        """
        Get pull request details.

        Args:
            repo: Repository name (owner/repo)
            pr_number: PR number

        Returns:
            PR data or None if not found
        """
        if not self._gh:
            return None

        try:
            return await self._gh.get_pr(repo, pr_number)
        except Exception as e:
            logger.error(f"Failed to get PR: {e}")
            return None

    async def stop(self) -> None:
        """Stop the GitHub connector."""
        self._gh = None
        self._callback = None
        self.state = ConnectorState.STOPPED
        logger.info(f"GitHubConnector stopped: {self.id}")

    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
        routing_metadata: dict[str, Any] | None = None,
    ) -> ConnectorEvent:
        """Create a standardized GitHub event."""
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
            routing_metadata=routing_metadata or {},
        )


class _GitHubAPIClient:
    """
    Internal GitHub API client.

    A lightweight client for GitHub App authentication and API calls.
    """

    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self._token: str | None = None
        self._installation_tokens: dict[int, str] = {}

    async def _get_installation_token(self, installation_id: int) -> str:
        """Get installation access token."""
        # In production, use PyGithub or gidgethub
        # This is a simplified implementation
        if installation_id in self._installation_tokens:
            return self._installation_tokens[installation_id]

        # Would need to implement JWT signing and token exchange
        # For now, return placeholder
        token = f"ghs_{installation_id}"
        self._installation_tokens[installation_id] = token
        return token

    async def create_issue_comment(
        self,
        repo: str,
        issue_number: int,
        body: str,
    ) -> None:
        """Create an issue/PR comment."""
        # In production, use:
        # POST /repos/{owner}/{repo}/issues/{issue_number}/comments
        logger.info(f"Would create comment on {repo}#{issue_number}: {body[:50]}...")

    async def get_pr(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Get PR details."""
        # In production, use:
        # GET /repos/{owner}/{repo}/pulls/{pull_number}
        return {
            "number": pr_number,
            "title": f"PR #{pr_number}",
            "state": "open",
        }
