# Use Ubuntu 24.04 as base image
FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    python3-full \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install podcastfy from PyPI
RUN pip install --no-cache-dir podcastfy

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Verify installations
RUN echo "Verifying installations:" && \
    echo "Ubuntu version:" && cat /etc/os-release && \
    echo "FFmpeg version:" && ffmpeg -version && \
    echo "Python version:" && python3 --version && \
    echo "Pip version:" && pip --version && \
    echo "Installed packages:" && pip list

# Command to run when container starts
CMD ["python3"]
