# Harness Cloud

Docker-based AI Agent sandbox platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER BROWSER (Vue + TS)                      │
│                              ↓ WebSocket                         │
└────────────────────────────────────┼────────────────────────────┘
                                     │
                                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                        GATEWAY (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Container   │  │ Rate        │  │ Auth        │             │
│  │ Manager     │  │ Limiter     │  │ (JWT)       │             │
│  └──────┬──────┘  └─────────────┘  └─────────────┘             │
│         │                                                       │
│         ↓ Docker API                                            │
└────────────────────────────────────┼────────────────────────────┘
                                     │
                                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CONTAINER AGENT (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ SDK Bridge  │  │ Memory      │                               │
│  │ (asyncio)   │  │ Limit       │                               │
│  └──────┬──────┘  └─────────────┘                               │
│         ↓                                                       │
│  ┌─────────────┐                                                │
│  │ AgentHarness│                                                │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Two-Layer Authentication

```
Client → Gateway (JWT) → Agent (API Key)
```

| Layer | Component | Credential | Purpose |
|-------|-----------|------------|---------|
| Gateway | Gateway WebSocket | JWT Token | User authentication |
| Agent | Agent WebSocket | API Key | LLM provider authentication |

## Testing

### 1. Local Development (without Docker)

**Test Agent service directly**:
```bash
cd packages/cloud
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000
```

**Connect and authenticate**:
```bash
wscat -c ws://localhost:8000/ws/run

# Authenticate with API key
> {"type": "auth", "payload": {"api_key": "your-api-key", "provider": "anthropic"}}
< {"type": "auth_success", "payload": {"provider": "anthropic", "model": "claude-sonnet-4-6"}}

# Send run request
> {"type": "run_request", "payload": {"prompt": "Hello"}}
```

**Authentication examples**:
```bash
# Anthropic API
> {"type": "auth", "payload": {"api_key": "sk-ant-xxx"}}

# OpenAI API
> {"type": "auth", "payload": {"api_key": "sk-xxx", "provider": "openai", "model": "gpt-4o"}}

# Custom OpenAI-compatible API
> {"type": "auth", "payload": {"api_key": "your-key", "provider": "openai", "base_url": "https://your-api.com/v1", "model": "your-model"}}
```

### 2. Docker Full Environment

**Build images**:
```bash
cd packages/cloud
./scripts/build.sh
```

The build script automatically detects:
- Current user UID and username
- Docker group GID (for docker.sock access)

**Start services** (copy the command from build.sh output):
```bash
DOCKER_USER=<your_username> DOCKER_UID=<your_uid> DOCKER_GID=<docker_gid> docker-compose up -d
```

> **Important**: After modifying any code, you must rebuild images (`./scripts/build.sh`) before testing. Otherwise, you'll be testing with old code.

**Check service health**:
```bash
curl http://localhost:8080/health
# Response: {"status": "healthy", "containers": 0}
```

**Create session and connect**:
```bash
# Step 1: Create session (returns session_id)
curl -X POST http://localhost:8080/api/sessions
# Response: {"session_id": "abc123", "container_id": "a1b2c3d"}

# Step 2: Connect and authenticate
# Option A: Use Python test script (recommended)
python test_ws.py abc123 your-api-key anthropic

# Option B: Manual wscat (must send auth within 30 seconds)
wscat -c ws://localhost:8080/ws/session/abc123
> {"type": "auth", "token": "test-token"}      # Gateway auth
> {"type": "auth", "payload": {"api_key": "your-api-key", "provider": "anthropic"}}  # Agent auth
< {"type": "auth_success", ...}

# Step 3: Send run requests
> {"type": "run_request", "payload": {"prompt": "Hello"}}
```

> **Note**: Gateway authentication is in testing mode and accepts any non-empty token. Production deployment requires proper JWT authentication system.

## WebSocket Protocol

### Message Flow (Auth-First Protocol)

```
Client                          Agent
  │                               │
  │──── auth ────────────────────>│
  │<─── auth_success ─────────────│
  │                               │
  │──── run_request ─────────────>│
  │<─── ack ──────────────────────│
  │<─── stream_chunk ─────────────│
  │<─── tool_call ────────────────│
  │<─── tool_result ──────────────│
  │<─── run_result ───────────────│
  │                               │
  │──── run_request ─────────────>│  (no auth needed)
  │<─── ack ──────────────────────│
  │...                            │
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `auth` | Client → Server | Authenticate with API credentials |
| `auth_success` | Server → Client | Authentication successful |
| `auth_failed` | Server → Client | Authentication failed |
| `run_request` | Client → Server | Execute a task |
| `ack` | Server → Client | Request acknowledged |
| `stream_chunk` | Server → Client | Streaming text chunk |
| `tool_call` | Server → Client | Tool call started |
| `tool_result` | Server → Client | Tool execution result |
| `run_result` | Server → Client | Final execution result |
| `error` | Server → Client | Error occurred |
| `interrupt` | Client → Server | Interrupt execution |
| `interrupted` | Server → Client | Execution interrupted |
| `ping/pong` | Both | Heartbeat |

### Auth Payload Options

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `api_key` | Yes | - | LLM provider API key |
| `provider` | No | `"anthropic"` | `"anthropic"` or `"openai"` |
| `base_url` | No | - | Custom API endpoint |
| `model` | No | `"claude-sonnet-4-6"` | Model name |
| `max_iterations` | No | `10` | Max agent loop iterations |
| `temperature` | No | `1.0` | LLM temperature |
| `system_prompt` | No | `""` | System prompt |

## Directory Structure

```
packages/cloud/
├── src/harness_cloud/
│   ├── common/
│   │   └── messages.py       # WebSocket message protocol
│   ├── agent/
│   │   ├── main.py           # FastAPI entry + WebSocket
│   │   ├── sdk_bridge.py     # SDK integration layer
│   │   ├── session_sync.py   # Session state sync
│   │   └── config.py         # Agent configuration
│   └── gateway/
│       ├── main.py           # Gateway FastAPI entry
│       ├── container_manager.py  # Abstract interface
│       ├── docker_manager.py     # Docker implementation
│       ├── tunnel.py         # WebSocket tunnel
│       ├── auth.py           # JWT authentication
│       ├── rate_limiter.py   # Redis rate limiter
│       └── config.py         # Gateway configuration
├── docker/
│   ├── agent.Dockerfile      # Agent container image
│   └── gateway.Dockerfile    # Gateway container image
├── docker-compose.yml        # Docker Compose config
└── scripts/
    └── build.sh              # Build script
```

## Security

### Container Lifecycle Management

Containers are automatically cleaned up using a three-layer strategy:

| Trigger | Action | Timeout |
|---------|--------|---------|
| WebSocket disconnect | Mark as draining → cleanup | 30s graceful shutdown |
| Idle timeout | Periodic cleanup | 15 minutes |
| User limit exceeded | Evict oldest container | 3 containers per user |

**State Flow**:
```
[running] ── disconnect ──→ [draining] ── 30s ──→ [removed]
    │
    └─ idle 15min ──────────────────────────→ [removed]
```

**Configuration** (environment variables):
```bash
HARNESS_CONTAINER_IDLE_TIMEOUT=900    # 15 minutes
HARNESS_GRACEFUL_SHUTDOWN_TIMEOUT=30  # seconds
HARNESS_MAX_CONTAINERS_PER_USER=3
```

### Container Isolation (ADR-004)

- `pids_limit`: 100 (prevent fork bombs)
- `internal_network`: No external internet access
- `read_only_root_fs`: Read-only filesystem
- `cap_drop`: ALL (drop all capabilities)

### Docker Socket (ADR-007)

- Gateway and Agent run as non-root user
- User UID matches host user (auto-detected at build time)
- Docker group GID set at runtime via `group_add`
- docker.sock mounted read-only
- Production: Use K8sPodManager or Docker Rootless

### Token Authentication (ADR-005)

- JWT token passed in first WebSocket message (not URL)
- Prevents token leakage in logs/headers
- 15-minute expiry with refresh mechanism

## Documentation

See `docs/` directory for detailed design documents:

- `01-overview.md` - Architecture overview
- `02-agent.md` - Agent glue layer design
- `03-gateway.md` - Gateway control layer
- `05-messages.md` - WebSocket protocol
- `06-deployment.md` - Deployment guide
