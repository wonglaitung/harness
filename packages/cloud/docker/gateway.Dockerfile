# Gateway Dockerfile
#
# Security considerations (ADR-007):
# - Runs as non-root user (member of docker group)
# - docker.sock mounted read-only
# - Minimal attack surface
# - UID/GID should match host user for volume permissions
# - Docker group GID is set at runtime via --group-add
#
# Reference: packages/cloud/docs/06-deployment.md

FROM python:3.11-slim

# Build arguments for user configuration
ARG DOCKER_USER=appuser
ARG DOCKER_UID=1000

# Create user with specified UID
# Note: docker group membership is set at runtime via --group-add
RUN groupadd -g $DOCKER_UID $DOCKER_USER && \
    useradd -m -u $DOCKER_UID -g $DOCKER_USER $DOCKER_USER

# Install Docker CLI (for docker.sock access)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy gateway code (relative to build context)
COPY packages/cloud/src/harness_cloud /app/harness_cloud

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    websockets \
    pydantic \
    pydantic-settings \
    python-jose[cryptography] \
    docker \
    redis \
    httpx

# Switch to non-root user
USER $DOCKER_USER

EXPOSE 8080

# Run gateway service
CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]