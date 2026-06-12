# Agent Dockerfile
#
# Multi-stage build for optimized image size.
# Builds SDK wheel separately, then copies to runtime image.
#
# Security considerations:
# - Runs as non-root user
# - Minimal attack surface
#
# Build context: /data/harness (from build.sh)
# Reference: packages/cloud/docs/06-deployment.md

# Stage 1: Build SDK wheel
FROM python:3.11-slim AS sdk-builder

WORKDIR /build

# Copy SDK source (relative to build context)
COPY packages/sdk /build/sdk

# Build wheel
RUN pip install --no-cache-dir build && \
    cd sdk && \
    python -m build --wheel

# Stage 2: Runtime image
FROM python:3.11-slim

# Build arguments for user configuration
ARG DOCKER_USER=appuser
ARG DOCKER_UID=1000

# Create user with specified UID
RUN groupadd -g $DOCKER_UID $DOCKER_USER && \
    useradd -m -u $DOCKER_UID -g $DOCKER_USER $DOCKER_USER

WORKDIR /app

# Copy SDK wheel from builder
COPY --from=sdk-builder /build/sdk/dist/*.whl /tmp/

# Install SDK and dependencies
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy agent code (relative to build context)
COPY packages/cloud/src/harness_cloud /app/harness_cloud

# Set PYTHONPATH so Python can find harness_cloud module
ENV PYTHONPATH=/app

# Install agent dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    websockets \
    pydantic \
    pydantic-settings

# Create workspace directory and set ownership
RUN mkdir /workspace && chown $DOCKER_USER:$DOCKER_USER /workspace
WORKDIR /workspace

# Switch to non-root user
USER $DOCKER_USER

EXPOSE 8000

# Run agent service
CMD ["uvicorn", "harness_cloud.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]