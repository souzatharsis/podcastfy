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
    
WORKDIR /app
# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app


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
CMD ["uvicorn", "podcastfy.api.fast_app:app", "--host", "0.0.0.0", "--port", "8000"]
