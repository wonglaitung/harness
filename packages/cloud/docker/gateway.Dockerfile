# Gateway Dockerfile
#
# Security considerations (ADR-007):
# - Runs as non-root user (marcowong, uid=1000)
# - docker.sock mounted read-only
# - User is in docker group for docker.sock access
#
# Build context: /data/harness (from docker-compose)
# Reference: packages/cloud/docs/06-deployment.md

FROM python:3.11-slim

# Create user with same uid/gid as host user (marcowong)
# This allows docker.sock access since host user is in docker group
RUN groupadd -g 1001 docker && \
    useradd -m -u 1000 -G docker marcowong

# Install Docker CLI (for docker.sock access)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy gateway code (relative to build context: /data/harness)
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

# Set ownership for app directory
RUN chown -R marcowong:marcowong /app

# Switch to non-root user
USER marcowong

EXPOSE 8080

# Run gateway service
CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
