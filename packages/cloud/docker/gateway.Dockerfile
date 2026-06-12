# Gateway Dockerfile
#
# Security considerations (ADR-007):
# - docker.sock mounted read-only
# - Minimal attack surface
#
# Note: For docker.sock access, container needs appropriate permissions.
# In production, use Docker Rootless or container orchestration API.
#
# Build context: /data/harness (from docker-compose)
# Reference: packages/cloud/docs/06-deployment.md

FROM python:3.11-slim

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

EXPOSE 8080

# Run gateway service
# Note: Running as root for docker.sock access (MVP stage)
# Production: Use Docker Rootless or K8sPodManager
CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
