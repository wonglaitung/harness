#!/bin/bash
#
# Build Docker images for Harness Cloud
#
# Usage:
#   ./build.sh [--no-cache]
#
# Options:
#   --no-cache    Force rebuild without cache

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

NO_CACHE=""
if [ "$1" == "--no-cache" ]; then
    NO_CACHE="--no-cache"
fi

echo "Building Harness Cloud images..."
echo "Project root: $PROJECT_ROOT"

# Build Agent image
echo ""
echo "=== Building Agent image ==="
docker build \
    $NO_CACHE \
    -f "$SCRIPT_DIR/../docker/agent.Dockerfile" \
    -t harness-agent:latest \
    "$PROJECT_ROOT"

# Build Gateway image
echo ""
echo "=== Building Gateway image ==="
docker build \
    $NO_CACHE \
    -f "$SCRIPT_DIR/../docker/gateway.Dockerfile" \
    -t harness-gateway:latest \
    "$PROJECT_ROOT"

echo ""
echo "=== Build complete ==="
echo "Images built:"
docker images | grep -E "harness-(agent|gateway)"

echo ""
echo "To start services:"
echo "  cd packages/cloud && docker-compose up -d"
