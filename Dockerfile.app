# Application Dockerfile using pre-built base image
# This builds FAST because dependencies are already compiled
# Use this for rapid iteration on code changes

ARG BASE_IMAGE=unitone-agentgateway-base:latest

# ============================================================================
# Stage 1: UI Build (fast - npm packages cached in base)
# ============================================================================
FROM docker.io/library/node:23.11.0-bookworm AS ui-builder
WORKDIR /app

# Copy package files and install (can be cached)
COPY agentgateway/ui/package*.json ./
RUN npm install

# Copy UI source
COPY agentgateway/ui ./

# Apply UnitOne UI customizations (overrides default UI files)
COPY ui-customizations/ ./

# Build UI
RUN npm run build

# ============================================================================
# Stage 2: Application Build (FAST - uses pre-built dependencies)
# ============================================================================
FROM ${BASE_IMAGE} AS app-builder

# Copy source code (the only thing that changes frequently)
# Copy workspace files
COPY agentgateway/Cargo.toml ./Cargo.toml
COPY agentgateway/Cargo.lock ./Cargo.lock
COPY agentgateway/crates ./crates/

# Build application (dependencies already compiled!)
RUN cargo build --release --features ui

# ============================================================================
# Stage 3: Runtime Image
# ============================================================================
FROM docker.io/library/debian:bookworm-slim AS runtime

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy binary
COPY --from=app-builder /build/target/release/agentgateway /usr/local/bin/

# Copy UI assets
COPY --from=ui-builder /app/out /opt/agentgateway/ui

WORKDIR /opt/agentgateway

# Expose ports
EXPOSE 8080 15000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/usr/local/bin/agentgateway", "--version"] || exit 1

ENTRYPOINT ["/usr/local/bin/agentgateway"]
CMD ["--file", "/etc/agentgateway/config.yaml"]
