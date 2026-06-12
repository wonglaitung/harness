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
# Build context is harness root (parent of packages)
BUILD_CONTEXT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

NO_CACHE=""
if [ "$1" == "--no-cache" ]; then
    NO_CACHE="--no-cache"
fi

echo "Building Harness Cloud images..."
echo "Build context: $BUILD_CONTEXT"

# Build Agent image
echo ""
echo "=== Building Agent image ==="
docker build \
    $NO_CACHE \
    -f "$SCRIPT_DIR/../docker/agent.Dockerfile" \
    -t harness-agent:latest \
    "$BUILD_CONTEXT"

# Build Gateway image
echo ""
echo "=== Building Gateway image ==="
docker build \
    $NO_CACHE \
    -f "$SCRIPT_DIR/../docker/gateway.Dockerfile" \
    -t harness-gateway:latest \
    "$BUILD_CONTEXT"

echo ""
echo "=== Build complete ==="
echo "Images built:"
docker images | grep -E "harness-(agent|gateway)"

echo ""
echo "To start services:"
echo "  cd packages/cloud && docker-compose up -d"
