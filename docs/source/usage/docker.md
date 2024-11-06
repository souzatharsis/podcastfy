# Docker Setup Guide for Podcastfy

This guide explains how to use Docker to run Podcastfy in your local environment or for development.

## Prerequisites

- Docker installed on your system [1]
- Docker Compose [1]
- API keys [2]

[1] See Appendix A for detailed installation instructions.
[2] See [config.md](https://github.com/souzatharsis/podcastfy/blob/main/usage/config.md) for more details.

## Available Images

Podcastfy provides pre-built Docker images through GitHub Container Registry (ghcr.io):

1. **Production Image**: `ghcr.io/souzatharsis/podcastfy:latest`
   - Contains the latest PyPI release
   - Recommended for production use

2. **Development Image**: `ghcr.io/souzatharsis/podcastfy:dev`
   - Includes development tools and dependencies
   - Used for contributing and development

## Deployment

### Quick Deployment Steps

1. Create a new directory and navigate to it:
```bash
mkdir -p /path/to/podcastfy
cd /path/to/podcastfy
```

2. Create a `.env` file with your API keys (see [config.md](https://github.com/souzatharsis/podcastfy/blob/main/usage/config.md) for more details):
```plaintext
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional: only needed for OpenAI TTS
```

3. Create a `docker-compose.yml`:
```yaml
version: '3.8'

services:
  podcastfy:
    image: ghcr.io/souzatharsis/podcastfy:latest
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    command: python3 -m podcastfy.server
    healthcheck:
      test: ["CMD", "python3", "-c", "import podcastfy"]
      interval: 30s
      timeout: 10s
      retries: 3
```

4. Pull and start the container:
```bash
docker pull ghcr.io/souzatharsis/podcastfy:latest
docker-compose up podcastfy
```

The service will be available at `http://localhost:8000`

### Directory Structure
```
/path/to/podcastfy/
├── .env                  # Environment variables
└── docker-compose.yml    # Docker Compose configuration
```

## Development Setup

### Using Pre-built Development Image

1. Pull the development image:
```bash
docker pull ghcr.io/souzatharsis/podcastfy:dev
```

2. Clone the repository and start development environment:
```bash
git clone https://github.com/souzatharsis/podcastfy.git
cd podcastfy
docker-compose up podcastfy-dev
```

### Building Locally

Alternatively, you can build the images locally:
```bash
# Build production image
docker-compose build podcastfy

# Build development image
docker-compose build podcastfy-dev
```

## Running Tests

Run the test suite using:
```bash
docker-compose up test
```

This will run tests in parallel using pytest-xdist.

## Environment Variables

Required environment variables:
- `GEMINI_API_KEY` - Your Google Gemini API key
- `OPENAI_API_KEY` - Your OpenAI API key (optional: only needed for OpenAI TTS)

## Container Details

### Production Container
- Based on Ubuntu 24.04
- Installs Podcastfy from PyPI
- Includes FFmpeg for audio processing
- Runs in a Python virtual environment
- Exposed port: 8000

### Development Container
- Based on Ubuntu 24.04
- Includes development tools (flake8, pytest)
- Mounts local code for live development
- Runs in editable mode (`pip install -e .`)
- Exposed port: 8001

## Continuous Integration

The Docker images are automatically:
- Built and tested on every push to main branch
- Built and tested for all pull requests
- Published to GitHub Container Registry
- Tagged with version numbers for releases (v*.*.*)

## Health Checks

All services include health checks that:
- Run every 30 seconds
- Verify Podcastfy can be imported
- Timeout after 10 seconds
- Retry up to 3 times

## Common Commands

```bash
# Pull latest production image
docker pull ghcr.io/souzatharsis/podcastfy:latest

# Pull development image
docker pull ghcr.io/souzatharsis/podcastfy:dev

# Start production service
docker-compose up podcastfy

# Start development environment
docker-compose up podcastfy-dev

# Run tests
docker-compose up test

# Build images locally
docker-compose build

# View logs
docker-compose logs

# Stop all containers
docker-compose down
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify your `.env` file exists and contains valid API keys
   - Check if the environment variables are properly passed to the container

2. **Port Conflicts**
   - Ensure ports 8000 (production) and 8001 (development) are available
   - Modify the port mappings in `docker-compose.yml` if needed

3. **Volume Mounting Issues (Development)**
   - Verify the correct path to your local code
   - Check permissions on the mounted directories

4. **Image Pull Issues**
   - Ensure you have access to the GitHub Container Registry
   - If you see "unauthorized" errors, the image might be private
   - Try authenticating with GitHub: `docker login ghcr.io -u YOUR_GITHUB_USERNAME`

### Verifying Installation

You can verify your installation by checking if the package can be imported:
```bash
# Check production version
docker run --rm ghcr.io/souzatharsis/podcastfy:latest python3 -c "import podcastfy"

# Check development setup
docker-compose exec podcastfy-dev python3 -c "import podcastfy"
```

## System Requirements

Minimum requirements:
- Docker Engine 20.10.0 or later
- Docker Compose 2.0.0 or later
- Sufficient disk space for Ubuntu base image (~400MB)
- Additional space for Python packages and FFmpeg

## Support

If you encounter any issues:
1. Check the container logs: `docker-compose logs`
2. Verify all prerequisites are installed
3. Ensure all required environment variables are set
4. Open an issue on the [Podcastfy GitHub repository](https://github.com/souzatharsis/podcastfy/issues)

## Appendix A: Detailed Installation Guide

### Installing Docker

#### Windows
1. Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - For Windows 10/11 Pro, Enterprise, or Education: Enable WSL 2 and Hyper-V
   - For Windows 10 Home: Enable WSL 2
2. After installation, start Docker Desktop
3. Verify installation:
```bash
docker --version
```

#### macOS
1. Download and install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - For Intel chip: Download Intel package
   - For Apple chip: Download Apple Silicon package
2. After installation, start Docker Desktop
3. Verify installation:
```bash
docker --version
```

#### Ubuntu/Debian
```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group (optional, to run docker without sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
```

#### Other Linux Distributions
- [CentOS](https://docs.docker.com/engine/install/centos/)
- [Fedora](https://docs.docker.com/engine/install/fedora/)
- [RHEL](https://docs.docker.com/engine/install/rhel/)

### Installing Docker Compose

Docker Compose is included with Docker Desktop for Windows and macOS. For Linux:

```bash
# Download the current stable release
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Apply executable permissions
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Post-Installation Steps

1. Verify Docker is running:
```bash
docker run hello-world
```

2. Configure Docker to start on boot (Linux only):
```bash
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
```

## Appendix B: Getting API Keys

### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create or sign in to your Google account
3. Click "Create API Key"
4. Copy and save your API key

### OpenAI API Key
You only need an OpenAI API key if you want to use the OpenAI Text-to-Speech model.
1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create or sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy and save your API key

## Appendix C: Installation Validation

After installing all prerequisites, verify everything is set up correctly:

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Verify Docker daemon is running
docker ps

# Test Docker functionality
docker run hello-world
```
