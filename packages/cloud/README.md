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

## Testing

### 1. Local Development (without Docker)

**Test Agent service** (SDK execution layer inside container):
```bash
cd packages/cloud
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000
```

Test with `wscat`:
```bash
# Install wscat
npm install -g wscat

# Connect WebSocket
wscat -c ws://localhost:8000/ws/run

# Step 1: Authenticate first
> {"type": "auth", "payload": {"api_key": "your-api-key", "provider": "anthropic"}}
# Response: {"type": "auth_success", "payload": {"provider": "anthropic", "model": "claude-sonnet-4-6"}}

# Step 2: Send run request (no API key needed after auth)
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

**Run request with optional overrides**:
```bash
# Override model for specific request
> {"type": "run_request", "payload": {"prompt": "Hello", "model": "claude-opus-4-6"}}
```

**Configuration options in auth payload**:
- `api_key`: API key (required)
- `provider`: "anthropic" (default) or "openai"
- `base_url`: Custom API endpoint (for OpenAI-compatible APIs)
- `model`: Model name (default: "claude-sonnet-4-6")
- `max_iterations`: Max agent loop iterations (default: 10)
- `temperature`: LLM temperature (default: 1.0)

### 2. Docker Full Environment

**Build images and start services**:
```bash
cd packages/cloud
./scripts/build.sh
docker-compose up -d
```

**Check service health**:
```bash
curl http://localhost:8080/health
```

**Create session**:
```bash
curl -X POST http://localhost:8080/api/sessions
# Response: {"session_id": "abc123", "container_id": "a1b2c3d"}
```

**Connect WebSocket**:
```bash
wscat -c ws://localhost:8080/ws/session/abc123
# Send auth message first:
> {"type": "auth", "token": "your-jwt-token"}
```

### 3. Required Configuration

Before testing, configure:

1. **API Key** - Set in `agent/config.py` or environment variable
2. **JWT Secret** - Default in docker-compose, change for production
3. **Redis** - Auto-started by docker-compose

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

### Container Isolation (ADR-004)

- `pids_limit`: 100 (prevent fork bombs)
- `internal_network`: No external internet access
- `read_only_root_fs`: Read-only filesystem
- `cap_drop`: ALL (drop all capabilities)

### Docker Socket (ADR-007)

- Gateway runs as non-root user
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
