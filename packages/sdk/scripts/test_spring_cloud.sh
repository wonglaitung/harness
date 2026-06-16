#!/bin/bash
# Quick test script for Spring Cloud integration
#
# Usage:
#   ./scripts/test_spring_cloud.sh [unit|integration|e2e|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$SDK_DIR")"

cd "$SDK_DIR"

PYTHONPATH="src"

case "${1:-all}" in
    unit)
        echo "Running unit tests..."
        PYTHONPATH="$PYTHONPATH" pytest tests/test_spring_cloud.py -v --tb=short
        ;;

    integration)
        echo "Running FastAPI integration tests..."
        PYTHONPATH="$PYTHONPATH" pytest tests/integration/test_fastapi_app.py -v --tb=short
        ;;

    e2e)
        echo "Running E2E tests (requires Docker Compose)..."

        # Check if service is running
        if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "Starting Docker Compose..."
            docker-compose -f docker/docker-compose.test.yml up -d

            echo "Waiting for service to be ready..."
            sleep 10

            # Wait for health check
            for i in {1..30}; do
                if curl -s http://localhost:8000/health | grep -q "healthy"; then
                    echo "Service is ready!"
                    break
                fi
                echo "Waiting... ($i/30)"
                sleep 2
            done
        fi

        PYTHONPATH="$PYTHONPATH" pytest tests/integration/test_spring_cloud_e2e.py -v --tb=short
        ;;

    all)
        echo "Running all tests..."
        PYTHONPATH="$PYTHONPATH" pytest tests/test_spring_cloud.py tests/integration/test_fastapi_app.py -v --tb=short
        ;;

    *)
        echo "Unknown test type: $1"
        echo "Usage: $0 [unit|integration|e2e|all]"
        exit 1
        ;;
esac

echo ""
echo "Test completed!"