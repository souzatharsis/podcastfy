# Base Stage
# - Pin the base image for all stages
# - Set common environment variables
# - Install shared runtime dependencies
FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    # Tweak Python to run better in Docker
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*


# Builder Stage
# - Install build tools (because pip may need to compile some packages)
# - Install podcastfy into a "portable" virtual environment
FROM base AS builder

# Install build tools if needed by podcastfy or its dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-full \
      python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir podcastfy

# Verify installations – this step can help debug the build process.
RUN echo "Verifying installations:" && \
    echo "Python version:" && python3 --version && \
    echo "Pip version:" && pip --version && \
    echo "Installed packages:" && pip list

# Runtime Stage
# - Minimal image with only runtime dependencies and non-full python installation
# - Using a non-root user for extra security
# - Copying the virtual environment from the builder stage,
#   leaving the compiler toolchain behind
FROM base AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 --system nonroot && \
    useradd --uid 1001 --system --gid 1001 nonroot

USER nonroot:nonroot

# Needed because of the ./data directory permissions
WORKDIR /home/nonroot

# Copy only the virtual environment from the builder stage.
COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Shouldn't it be ENTRYPOINT ["python3"] instead?
CMD ["python3"]
