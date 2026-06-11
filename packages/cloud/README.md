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

## Quick Start

### Build Images

```bash
cd packages/cloud
./scripts/build.sh
```

### Start Services

```bash
docker-compose up -d
```

### Check Health

```bash
curl http://localhost:8080/health
```

### Create Session

```bash
curl -X POST http://localhost:8080/api/sessions
# Response: {"session_id": "abc123", "container_id": "a1b2c3d"}
```

### Connect WebSocket

```bash
wscat -c ws://localhost:8080/ws/session/abc123
# Send auth message first:
> {"type": "auth", "token": "your-jwt-token"}
```

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

## Development

### Run Agent Locally

```bash
cd packages/cloud
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000
```

### Run Gateway Locally

```bash
cd packages/cloud
uv run uvicorn harness_cloud.gateway.main:app --reload --port 8080
```

### WebSocket Testing

```bash
wscat -c ws://localhost:8000/ws/run
> {"type": "run_request", "payload": {"prompt": "Hello"}}
```

## Documentation

See `docs/` directory for detailed design documents:

- `01-overview.md` - Architecture overview
- `02-agent.md` - Agent glue layer design
- `03-gateway.md` - Gateway control layer
- `05-messages.md` - WebSocket protocol
- `06-deployment.md` - Deployment guide