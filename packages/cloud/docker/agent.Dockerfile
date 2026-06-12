# Agent Dockerfile
#
# Multi-stage build for optimized image size.
# Builds SDK wheel separately, then copies to runtime image.
#
# Build context: /data/harness/packages
# Reference: packages/cloud/docs/06-deployment.md

# Stage 1: Build SDK wheel
FROM python:3.11-slim AS sdk-builder

WORKDIR /build

# Copy SDK source (relative to build context: packages/)
COPY sdk /build/sdk

# Build wheel
RUN pip install --no-cache-dir build && \
    cd sdk && \
    python -m build --wheel

# Stage 2: Runtime image
FROM python:3.11-slim

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy SDK wheel from builder
COPY --from=sdk-builder /build/sdk/dist/*.whl /tmp/

# Install SDK and dependencies
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy agent code (relative to build context: packages/)
COPY cloud/src/harness_cloud /app/harness_cloud

# Install agent dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    websockets \
    pydantic \
    pydantic-settings

# Create workspace directory
RUN mkdir /workspace
WORKDIR /workspace

EXPOSE 8000

# Run agent service
CMD ["uvicorn", "harness_cloud.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
