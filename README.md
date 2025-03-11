# Hello World Flask Application

A simple Flask web application that displays a "Hello World" message with modern styling.

## Local Development Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

Visit: http://localhost:5000

## Docker Support

### Running with Docker

Pull and run the latest image:
```bash
docker pull ghcr.io/YOUR_GITHUB_USERNAME/poc-portal:latest
docker run -p 5000:5000 ghcr.io/YOUR_GITHUB_USERNAME/poc-portal:latest
```

### Building Locally
```bash
docker build -t poc-portal .
docker run -p 5000:5000 poc-portal
```

## CI/CD

This repository uses GitHub Actions to automatically build and push Docker images to GitHub Container Registry (ghcr.io) when code is pushed to the master branch.

The workflow:
1. Builds the Docker image
2. Pushes it to GitHub Container Registry with two tags:
   - `latest`
   - Git SHA (for version tracking)

To use the automated builds:
1. Ensure your repository has access to GitHub Container Registry
2. The `GITHUB_TOKEN` secret is automatically available to the workflow 