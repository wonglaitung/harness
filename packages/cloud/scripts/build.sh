#!/bin/bash
#
# Build Docker images for Harness Cloud
#
# Usage:
#   ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Detect host user UID and docker GID
DOCKER_UID=$(id -u)
DOCKER_GID=$(getent group docker | cut -d: -f3)
CONTAINER_USER=$(whoami)

if [ -z "$DOCKER_GID" ]; then
    echo "Warning: Could not detect docker group GID, using default 1001"
    DOCKER_GID=1001
fi

echo "Building Harness Cloud images..."
echo "Project root: $PROJECT_ROOT"
echo "Container user: $CONTAINER_USER (UID=$DOCKER_UID, docker GID=$DOCKER_GID)"

# Build Agent image
echo ""
echo "=== Building Agent image ==="
docker build \
    --no-cache \
    --build-arg DOCKER_USER="$CONTAINER_USER" \
    --build-arg DOCKER_UID="$DOCKER_UID" \
    -f "$PROJECT_ROOT/packages/cloud/docker/agent.Dockerfile" \
    -t harness-agent:latest \
    "$PROJECT_ROOT"

# Build Gateway image
echo ""
echo "=== Building Gateway image ==="
docker build \
    --no-cache \
    --build-arg DOCKER_USER="$CONTAINER_USER" \
    --build-arg DOCKER_UID="$DOCKER_UID" \
    -f "$PROJECT_ROOT/packages/cloud/docker/gateway.Dockerfile" \
    -t harness-gateway:latest \
    "$PROJECT_ROOT"

echo ""
echo "=== Build complete ==="
echo "Images built:"
docker images | grep -E "harness-(agent|gateway)"

echo ""
echo "To start services:"
echo "  cd packages/cloud && DOCKER_USER=$CONTAINER_USER DOCKER_UID=$DOCKER_UID DOCKER_GID=$DOCKER_GID docker-compose up -d"
