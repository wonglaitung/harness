"""
JWT authentication module.

Provides:
- Token creation
- Token validation
- User extraction from token

Reference: packages/cloud/docs/03-gateway.md (Auth section)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from harness_cloud.gateway.config import GatewayConfig


class User(BaseModel):
    """User information from JWT token."""

    id: str
    username: str = ""
    roles: list[str] = []


def create_token(
    user_id: str,
    config: GatewayConfig,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create JWT token.

    Args:
        user_id: User identifier
        config: Gateway configuration
        expires_minutes: Token expiry time (default from config)

    Returns:
        JWT token string
    """
    expires = expires_minutes or config.jwt_expire_minutes
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def verify_token(token: str, config: GatewayConfig) -> User:
    """
    Verify JWT token and extract user.

    Args:
        token: JWT token string
        config: Gateway configuration

    Returns:
        User information

    Raises:
        ValueError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
        )
        return User(
            id=payload["sub"],
            username=payload.get("username", ""),
            roles=payload.get("roles", []),
        )
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def refresh_token(token: str, config: GatewayConfig) -> str:
    """
    Refresh JWT token (extend expiry).

    Args:
        token: Current JWT token
        config: Gateway configuration

    Returns:
        New JWT token with extended expiry
    """
    user = verify_token(token, config)
    return create_token(user.id, config)