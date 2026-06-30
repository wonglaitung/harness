"""
Tests for Phase 4: Connectors.

This module tests:
- Connector types
- WebhookConnector
- SlackConnector
- GitHubConnector
- ConnectorManager
"""

from __future__ import annotations

import pytest

from harness.connectors.types import (
    ConnectorEvent,
    ConnectorState,
    ConnectorType,
    GitHubConfig,
    OutputChannel,
    OutputResult,
    RoutingKeys,
    SlackConfig,
    WebhookConfig,
)


class TestConnectorTypes:
    """Tests for connector type definitions."""

    def test_connector_type_values(self):
        """Test ConnectorType enum values."""
        assert ConnectorType.WEBHOOK.value == "webhook"
        assert ConnectorType.SLACK.value == "slack"
        assert ConnectorType.GITHUB.value == "github"
        assert ConnectorType.CUSTOM.value == "custom"

    def test_connector_state_values(self):
        """Test ConnectorState enum values."""
        assert ConnectorState.IDLE.value == "idle"
        assert ConnectorState.RUNNING.value == "running"
        assert ConnectorState.STOPPED.value == "stopped"
        assert ConnectorState.ERROR.value == "error"

    def test_routing_keys_constants(self):
        """Test RoutingKeys constants."""
        assert RoutingKeys.SLACK_THREAD_TS == "slack_thread_ts"
        assert RoutingKeys.SLACK_CHANNEL_ID == "slack_channel_id"
        assert RoutingKeys.GITHUB_PR_NUMBER == "github_pr_number"
        assert RoutingKeys.GITHUB_ISSUE_NUMBER == "github_issue_number"
        assert RoutingKeys.GITHUB_REPO == "github_repo"
        assert RoutingKeys.WEBHOOK_REQUEST_ID == "webhook_request_id"


class TestConnectorEvent:
    """Tests for ConnectorEvent."""

    def test_create_basic_event(self):
        """Test creating a basic ConnectorEvent."""
        event = ConnectorEvent(
            connector_type=ConnectorType.SLACK,
            connector_id="slack_123",
            event_type="slack.message",
            source="user_abc",
        )

        assert event.connector_type == ConnectorType.SLACK
        assert event.connector_id == "slack_123"
        assert event.event_type == "slack.message"
        assert event.source == "user_abc"
        assert event.payload == {}
        assert event.routing_metadata == {}

    def test_create_event_with_payload(self):
        """Test creating event with payload."""
        event = ConnectorEvent(
            connector_type=ConnectorType.GITHUB,
            connector_id="github_456",
            event_type="github.pull_request.opened",
            source="owner/repo",
            payload={"number": 42, "title": "Fix bug"},
            routing_metadata={RoutingKeys.GITHUB_PR_NUMBER: 42},
        )

        assert event.payload["number"] == 42
        assert event.routing_metadata[RoutingKeys.GITHUB_PR_NUMBER] == 42

    def test_is_command_property(self):
        """Test is_command property."""
        # Command event
        command_event = ConnectorEvent(
            connector_type=ConnectorType.SLACK,
            connector_id="slack_123",
            event_type="slack.command",
            source="user",
        )
        assert command_event.is_command is True

        # Regular event
        regular_event = ConnectorEvent(
            connector_type=ConnectorType.SLACK,
            connector_id="slack_123",
            event_type="slack.message",
            source="user",
        )
        assert regular_event.is_command is False


class TestOutputChannel:
    """Tests for OutputChannel."""

    def test_create_slack_channel(self):
        """Test creating Slack output channel."""
        channel = OutputChannel(
            type="slack",
            name="alerts",
            config={"channel": "#alerts"},
        )

        assert channel.type == "slack"
        assert channel.name == "alerts"
        assert channel.config["channel"] == "#alerts"

    def test_create_webhook_channel(self):
        """Test creating webhook output channel."""
        channel = OutputChannel(
            type="webhook",
            name="external_api",
            config={
                "url": "https://example.com/webhook",
                "headers": {"Authorization": "Bearer token"},
            },
        )

        assert channel.type == "webhook"
        assert channel.config["url"] == "https://example.com/webhook"


class TestOutputResult:
    """Tests for OutputResult."""

    def test_success_result(self):
        """Test successful output result."""
        result = OutputResult(
            channel_name="alerts",
            success=True,
            message="Message sent",
        )

        assert result.channel_name == "alerts"
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        """Test failed output result."""
        result = OutputResult(
            channel_name="alerts",
            success=False,
            error="Channel not found",
        )

        assert result.success is False
        assert result.error == "Channel not found"


class TestWebhookConfig:
    """Tests for WebhookConfig."""

    def test_create_config(self):
        """Test creating webhook config."""
        config = WebhookConfig(
            endpoint="/webhook/github",
            secret="whsec_123",
            rate_limit=100,
        )

        assert config.endpoint == "/webhook/github"
        assert config.secret == "whsec_123"
        assert config.rate_limit == 100


class TestSlackConfig:
    """Tests for SlackConfig."""

    def test_create_config(self):
        """Test creating Slack config."""
        config = SlackConfig(
            bot_token="xoxb-123",
            app_token="xapp-456",
            command_prefix="/harness",
        )

        assert config.bot_token == "xoxb-123"
        assert config.app_token == "xapp-456"
        assert config.command_prefix == "/harness"


class TestGitHubConfig:
    """Tests for GitHubConfig."""

    def test_create_config(self):
        """Test creating GitHub config."""
        config = GitHubConfig(
            app_id="123456",
            private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
            webhook_secret="whsec_789",
            events=["push", "pull_request"],
        )

        assert config.app_id == "123456"
        assert "push" in config.events
        assert "pull_request" in config.events


class TestWebhookConnector:
    """Tests for WebhookConnector."""

    @pytest.fixture
    def webhook(self):
        """Create a WebhookConnector instance."""
        from harness.connectors.webhook import WebhookConnector

        return WebhookConnector(
            config=WebhookConfig(
                endpoint="/webhook/test",
                secret="test_secret",
            )
        )

    def test_connector_type(self, webhook):
        """Test connector type."""
        assert webhook.connector_type == ConnectorType.WEBHOOK

    def test_initial_state(self, webhook):
        """Test initial state is IDLE."""
        assert webhook.state == ConnectorState.IDLE

    def test_create_event(self, webhook):
        """Test creating webhook event."""
        event = webhook.create_event(
            event_type="webhook.received",
            payload={"action": "push"},
            source="github",
            routing_metadata={"request_id": "abc123"},
        )

        assert event.connector_type == ConnectorType.WEBHOOK
        assert event.event_type == "webhook.received"
        assert event.routing_metadata["request_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_start_and_stop(self, webhook):
        """Test starting and stopping webhook connector."""

        async def callback(event):
            pass

        await webhook.start(callback)
        assert webhook.state == ConnectorState.RUNNING

        await webhook.stop()
        assert webhook.state == ConnectorState.STOPPED


class TestSlackConnector:
    """Tests for SlackConnector."""

    @pytest.fixture
    def slack(self):
        """Create a SlackConnector instance."""
        from harness.connectors.slack import SlackConnector

        return SlackConnector(
            config=SlackConfig(
                bot_token="xoxb-test",
            )
        )

    def test_connector_type(self, slack):
        """Test connector type."""
        assert slack.connector_type == ConnectorType.SLACK

    def test_create_event_with_routing(self, slack):
        """Test creating Slack event with routing metadata."""
        event = slack.create_event(
            event_type="slack.message",
            payload={"text": "Hello", "channel": "C123"},
            source="U456",
            routing_metadata={
                RoutingKeys.SLACK_THREAD_TS: "17123456.0001",
                RoutingKeys.SLACK_CHANNEL_ID: "C123",
            },
        )

        assert event.connector_type == ConnectorType.SLACK
        assert RoutingKeys.SLACK_THREAD_TS in event.routing_metadata


class TestGitHubConnector:
    """Tests for GitHubConnector."""

    @pytest.fixture
    def github(self):
        """Create a GitHubConnector instance."""
        from harness.connectors.github import GitHubConnector

        return GitHubConnector(
            config=GitHubConfig(
                app_id="123",
                private_key="test_key",
                webhook_secret="test_secret",
            )
        )

    def test_connector_type(self, github):
        """Test connector type."""
        assert github.connector_type == ConnectorType.GITHUB

    def test_create_event_with_pr_routing(self, github):
        """Test creating GitHub event with PR routing metadata."""
        event = github.create_event(
            event_type="github.pull_request.opened",
            payload={"number": 42, "title": "Fix bug"},
            source="owner/repo",
            routing_metadata={
                RoutingKeys.GITHUB_PR_NUMBER: 42,
                RoutingKeys.GITHUB_REPO: "owner/repo",
            },
        )

        assert event.connector_type == ConnectorType.GITHUB
        assert event.routing_metadata[RoutingKeys.GITHUB_PR_NUMBER] == 42


class TestConnectorManager:
    """Tests for ConnectorManager."""

    @pytest.fixture
    def mock_trigger_manager(self):
        """Create a mock TriggerManager."""

        class MockTriggerManager:
            def __init__(self):
                self.events = []

            async def enqueue_event(self, event):
                self.events.append(event)

        return MockTriggerManager()

    def test_register_connector(self, mock_trigger_manager):
        """Test registering a connector."""
        from harness.connectors import ConnectorManager
        from harness.connectors.webhook import WebhookConnector

        manager = ConnectorManager(mock_trigger_manager)
        webhook = WebhookConnector(
            config=WebhookConfig(endpoint="/webhook"),
        )

        connector_id = manager.register_connector(webhook)
        assert connector_id == webhook.id
        assert manager.connector_count == 1

    def test_register_output_channel(self, mock_trigger_manager):
        """Test registering output channel."""
        from harness.connectors import ConnectorManager

        manager = ConnectorManager(mock_trigger_manager)

        channel = OutputChannel(
            type="slack",
            name="alerts",
            config={"channel": "#alerts"},
        )

        name = manager.register_output_channel(channel)
        assert name == "alerts"
        assert "alerts" in manager.list_output_channels()

    @pytest.mark.asyncio
    async def test_route_event_to_trigger_manager(self, mock_trigger_manager):
        """Test routing event to TriggerManager."""
        from harness.connectors import ConnectorManager

        manager = ConnectorManager(mock_trigger_manager)

        event = ConnectorEvent(
            connector_type=ConnectorType.SLACK,
            connector_id="slack_123",
            event_type="slack.message",
            source="user",
            payload={"text": "Hello"},
            routing_metadata={"thread_ts": "17123456.0001"},
        )

        await manager._on_connector_event(event)

        assert len(mock_trigger_manager.events) == 1
        trigger_event = mock_trigger_manager.events[0]
        assert trigger_event.routing_metadata["thread_ts"] == "17123456.0001"
