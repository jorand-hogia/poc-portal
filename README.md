# Portal Application

A web portal that connects to external services and displays their data. Built with Flask and Docker.

## Features

- **Dashboard**: View data from connected external services
- **Settings**: Add, remove, and test external service connections
- **Docker Integration**: Run both the portal and a sample external service in containers
- **CI/CD Pipeline**: Automated builds and tests with GitHub Actions

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- Git

### Local Development Setup

1. Create a virtual environment:
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

### Docker Setup

1. Build and run the containers:
```bash
docker-compose up --build
```

This will start:
- Portal at http://localhost:5000
- External service at http://localhost:5001

2. Test the connection:
   - Go to Settings page (http://localhost:5000/settings)
   - Add a service with:
     - Name: Example Service
     - URL: http://external-service:5001/api/data
   - Test the connection
   - Go back to Dashboard to see the data

## Container Structure

- **Portal Container**: The main web application
- **External Service**: A sample API service for testing

## CI/CD

This repository uses GitHub Actions to automatically:
1. Build and test the Python application
2. Build Docker images
3. Simulate deployment

## Configuration

Service settings are stored in `config.json` which is mounted as a volume to persist configuration between container restarts.

## Development with Cursor

This project was developed using Cursor, an AI-powered code editor that provides:
- Code generation
- Debugging assistance
- Project organization
- Context-aware suggestions

## License

MIT 