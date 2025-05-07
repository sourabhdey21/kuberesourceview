# Kubernetes Resource Viewer

A modern web application to view and manage Kubernetes resources across all namespaces.

## Features

- View all Kubernetes resources across namespaces
- Modern, responsive user interface
- Real-time resource updates
- Detailed resource information
- Namespace filtering and search
- Node and cluster pricing insights (USD/INR)
- Docker and Docker Compose support

## Screenshots

### Nodes View
![Nodes View](image/README/1746638012845.png)

### Resources & Pricing
![Resources and Pricing](image/README/1746638014777.png)

## Setup

### Local (Python venv)
1. Install Python dependencies:
```bash
pip install -r requirements.txt
```
2. Configure Kubernetes access:
   - Ensure you have a valid kubeconfig file
   - The application will use your default kubeconfig location
3. Run the application:
```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```
4. Access the application at `http://localhost:5000`

### Docker Compose (Recommended)
1. Build and run the app:
```bash
docker-compose up --build
```
2. The app will be available at `http://localhost:5000`
3. Your local kubeconfig will be mounted for cluster access.

### Docker (Single Container)
1. Build the Docker image:
```bash
docker build -t kubeview .
```
2. Run the container:
```bash
docker run -d \
  -p 5000:5000 \
  -v ~/.kube:/root/.kube:ro \
  --name kubeview kubeview
```
3. The app will be available at `http://localhost:5000`

## Project Structure
- `app.py` - Main FastAPI application
- `templates/` - HTML templates
- `static/` - Frontend static files
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build file
- `docker-compose.yml` - Multi-container orchestration
- `.gitignore` - Git ignore rules

## Requirements
- Python 3.8+ (for local dev)
- Docker & Docker Compose (for containerized usage)
- Kubernetes cluster access
- Modern web browser

## API Documentation
FastAPI automatically generates API documentation. You can access it at:
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

## .gitignore
This project includes a `.gitignore` to exclude Python cache, virtual environments, editor files, logs, and sensitive files like `.env`.