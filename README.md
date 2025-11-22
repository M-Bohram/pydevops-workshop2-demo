# ClearList - Full-Stack Todo Application with Docker

A hands-on workshop project demonstrating a containerized full-stack application with Flask backend, Nginx frontend, PostgreSQL database, and Docker deployment.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Frontend & Nginx Configuration](#frontend--nginx-configuration)
3. [Backend & Logging](#backend--logging)
4. [Docker Compose: Networks & Volumes](#docker-compose-networks--volumes)
5. [Docker Hub: Repositories & Deployment](#docker-hub-repositories--deployment)

---

## Project Structure

### Directory Layout

```
clearlist/
├── docker-compose.yml          # Orchestrates all services
├── backend/                    # Flask API service
│   ├── Dockerfile             # Backend container definition
│   ├── app.py                 # Flask application with logging
│   └── requirements.txt       # Python dependencies
└── frontend/                   # Nginx + Static files
    ├── Dockerfile             # Frontend container definition
    ├── nginx.conf             # Nginx reverse proxy config
    ├── index.html             # Main HTML page
    ├── main.js                # Frontend JavaScript
    └── styles.css             # Styling
```

### Service Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ :8080
       ↓
┌─────────────────┐
│   Frontend      │
│ Nginx (Port 80) │
│   Reverse Proxy │
└────┬──────┬─────┘
     │      │
     │ /    │ /api, /uploads
     │      ↓
     │   ┌──────────────┐
     │   │   Backend    │
     │   │ Flask :5000  │
     │   └──────┬───────┘
     │          │
     │          ↓
     │   ┌──────────────┐
     │   │  Database    │
     └───┤ PostgreSQL   │
         │   :5432      │
         └──────────────┘
```

---

## Frontend & Nginx Configuration

### Nginx as Reverse Proxy

The frontend service uses Nginx to serve static files and proxy API requests to the backend.

**File: `frontend/nginx.conf`**

```nginx
server {
    listen 80;

    # Serve static frontend files
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri /index.html;
    }

    # Proxy API calls to Flask backend
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy file downloads to backend
    location /uploads/ {
        proxy_pass http://backend:5000/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Key Nginx Concepts

1. **Static File Serving**: The `/` location serves HTML, CSS, and JS files directly
2. **Reverse Proxy**: The `/api/` and `/uploads/` locations forward requests to the backend service
3. **Service Discovery**: Notice `http://backend:5000` - Docker Compose provides DNS resolution for service names!

### Frontend Dockerfile

**File: `frontend/Dockerfile`**

```dockerfile
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
COPY main.js /usr/share/nginx/html/
COPY styles.css /usr/share/nginx/html/
```

This lightweight Alpine-based image:
- Uses the official Nginx image (only ~24MB!)
- Copies our custom configuration
- Adds static web files

---

## Backend & Logging

### Flask Application Structure

The backend is a Flask REST API that demonstrates proper logging practices.

**File: `backend/app.py` (Key Sections)**

#### 1. Logging Configuration

```python
import logging
import sys

# Configure logging to STDOUT for Docker
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,   # Override Flask/Werkzeug handlers
)

logger = logging.getLogger("clearlist")
```

**Why log to STDOUT?**
- Docker captures container STDOUT/STDERR
- Enables centralized logging with `docker-compose logs`
- Follows 12-factor app principles

#### 2. Logging Levels in Action

```python
@app.route("/api/health")
def health():
    logger.debug("Health endpoint hit.")  # DEBUG: Development details
    return {"status": "ok"}

@app.route("/api/todos", methods=["GET"])
def list_todos():
    logger.debug("Fetching todos...")      # DEBUG: Function entry
    # ... database query ...
    logger.info(f"Returned {len(todos)} todos.")  # INFO: Important events
    return jsonify(todos)

@app.route("/api/todos", methods=["POST"])
def create_todo():
    if not title:
        logger.warning("Attempted todo creation without title.")  # WARNING: Invalid input
        return {"error": "Title required"}, 400

    try:
        # ... create todo ...
        logger.info(f"Created todo {todo['id']}")  # INFO: Success
        return jsonify(todo), 201
    except Exception as e:
        logger.error(f"Error creating todo: {e}")  # ERROR: Exception occurred
        return {"error": "Internal error"}, 500
```

### Logging Level Guide

| Level | Use Case | Example |
|-------|----------|---------|
| DEBUG | Development details | "Health endpoint hit." |
| INFO | Important events | "Created todo 42" |
| WARNING | Recoverable issues | "Invalid input received" |
| ERROR | Exceptions/errors | "Database connection failed" |
| CRITICAL | System failures | "Could not initialize DB" |

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend

# Follow logs (like tail -f)
docker-compose logs -f backend

# Last 50 lines
docker-compose logs --tail=50 backend
```

### Backend Dockerfile

**File: `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

# Install PostgreSQL client dependencies
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
```

**Key Details:**
- `PYTHONUNBUFFERED=1`: Ensures logs appear immediately (no buffering)
- Multi-stage approach: Install deps → Copy code
- Cleanup apt cache to reduce image size

---

## Docker Compose: Networks & Volumes

### Understanding the Configuration

**File: `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: clearlist
      POSTGRES_USER: clearlist
      POSTGRES_PASSWORD: clearlist
    volumes:
      - db-data:/var/lib/postgresql/data

  backend:
    build: ./backend
    image: docker.io/mbohram/backend:latest
    environment:
      DATABASE_URL: postgresql://clearlist:clearlist@db:5432/clearlist
      UPLOAD_FOLDER: /app/uploads
      LOG_LEVEL: INFO
    volumes:
      - backend-uploads:/app/uploads
    depends_on:
      - db

  frontend:
    build: ./frontend
    image: docker.io/mbohram/frontend:latest
    ports:
      - "8080:80"
    depends_on:
      - backend

volumes:
  db-data:
  backend-uploads:
```

### Networks (Implicit)

Docker Compose automatically creates a **default network** for all services:

```
Network: clearlist_default
├── db (resolvable as "db")
├── backend (resolvable as "backend")
└── frontend (resolvable as "frontend")
```

**How services communicate:**
- Backend → Database: `db:5432` (no IP needed!)
- Frontend → Backend: `backend:5000`
- Docker's embedded DNS resolves service names to container IPs

### Volumes Explained

#### 1. Named Volume: `db-data`

```yaml
volumes:
  - db-data:/var/lib/postgresql/data
```

**Purpose**: Persist PostgreSQL data between container restarts

```bash
# Inspect volume
docker volume inspect clearlist_db-data

# Where is data stored?
# Docker manages it: /var/lib/docker/volumes/clearlist_db-data/_data
```

#### 2. Named Volume: `backend-uploads`

```yaml
volumes:
  - backend-uploads:/app/uploads
```

**Purpose**: Store uploaded files persistently

### Volume Lifecycle Commands

```bash
# List volumes
docker volume ls

# Remove unused volumes
docker volume prune

# Remove specific volume (WARNING: deletes data!)
docker volume rm clearlist_db-data

# Backup a volume
docker run --rm -v clearlist_db-data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz /data
```

### Service Dependencies

```yaml
depends_on:
  - db  # Wait for db to start before backend
```

**Note**: `depends_on` ensures startup order but doesn't wait for "ready" state. For production, use health checks!

---

## Docker Hub: Repositories & Deployment

### Creating a Docker Hub Repository

#### Step 1: Create Account

1. Go to [hub.docker.com](https://hub.docker.com)
2. Sign up / Log in
3. Click "Create Repository"

#### Step 2: Repository Settings

- **Name**: `backend` (or any name)
- **Visibility**:
  - **Public**: Anyone can pull
  - **Private**: Only you (or your team) can access
- **Description**: Optional but recommended

**Naming Convention**: `username/repository:tag`
- Example: `mbohram/backend:latest`
- Example: `mbohram/backend:v1.0.0`

### Building and Pushing Images

#### Method 1: Build & Push Manually

```bash
# Log in to Docker Hub
docker login
# Enter username and password

# Build images with Docker Hub tags
docker build -t docker.io/mbohram/backend:latest ./backend
docker build -t docker.io/mbohram/frontend:latest ./frontend

# Push to Docker Hub
docker push docker.io/mbohram/backend:latest
docker push docker.io/mbohram/frontend:latest
```

#### Method 2: Build & Push with Docker Compose

```bash
# Build images (creates local images with tags from docker-compose.yml)
docker-compose build

# Push to Docker Hub
docker-compose push
```

**Important**: The `image:` field in `docker-compose.yml` must match your Docker Hub username!

```yaml
backend:
  build: ./backend
  image: docker.io/YOUR_USERNAME/backend:latest  # ← Change this!
```

### Pulling and Deploying

Once pushed to Docker Hub, anyone (if public) or your team (if private) can deploy:

```bash
# Pull images
docker pull docker.io/mbohram/backend:latest
docker pull docker.io/mbohram/frontend:latest

# Run with docker-compose
docker-compose pull  # Pull latest versions
docker-compose up -d  # Start services
```

### Private Repositories

For private repos, authenticate before pulling:

```bash
docker login docker.io
# Or specify credentials
docker login docker.io -u mbohram -p YOUR_PASSWORD

# Then pull
docker-compose pull
```

### Image Tagging Strategy

```bash
# Development
docker build -t mbohram/backend:dev ./backend

# Staging
docker build -t mbohram/backend:staging ./backend

# Production releases
docker build -t mbohram/backend:v1.0.0 ./backend
docker build -t mbohram/backend:latest ./backend

# Push all tags
docker push mbohram/backend:dev
docker push mbohram/backend:staging
docker push mbohram/backend:v1.0.0
docker push mbohram/backend:latest
```

---

## Running the Application

### Start Services

```bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Access the Application

- **Frontend**: http://localhost:8080
- **API Health**: http://localhost:8080/api/health
- **API Todos**: http://localhost:8080/api/todos

### Stop Services

```bash
# Stop containers (keeps volumes)
docker-compose down

# Stop and remove volumes (deletes data!)
docker-compose down -v
```

---

## Learning Exercises

### Exercise 1: Network Inspection

```bash
# List networks
docker network ls

# Inspect the default network
docker network inspect clearlist_default

# Find container IPs
docker-compose exec backend ping db
```

### Exercise 2: Volume Exploration

```bash
# Create a todo with file upload via the UI
# Then inspect the volume:
docker-compose exec backend ls -la /app/uploads

# Check volume size
docker system df -v
```

### Exercise 3: Logging Levels

```bash
# Change LOG_LEVEL in docker-compose.yml
LOG_LEVEL: DEBUG  # See all debug messages

# Restart backend
docker-compose up -d backend

# View verbose logs
docker-compose logs -f backend
```

### Exercise 4: Multi-Environment Deployment

Create `docker-compose.prod.yml`:

```yaml
services:
  backend:
    image: docker.io/mbohram/backend:v1.0.0  # Specific version
    environment:
      LOG_LEVEL: WARNING  # Less verbose in production
    restart: always
```

Deploy:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Key Takeaways

1. **Project Structure**: Organized into frontend, backend, and configuration files
2. **Nginx**: Acts as reverse proxy, routes `/api` to backend, serves static files
3. **Flask Logging**: Use appropriate log levels, log to STDOUT for Docker
4. **Docker Networks**: Services communicate via names (no hardcoded IPs!)
5. **Docker Volumes**: Persist data (database, uploads) across container lifecycles
6. **Docker Hub**: Central registry for sharing and deploying container images
7. **docker-compose**: Orchestrates multi-container applications with a single config file

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
docker-compose logs backend

# Restart a specific service
docker-compose restart backend
```

### Database Connection Errors

```bash
# Verify database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection from backend
docker-compose exec backend ping db
```

### Port Already in Use

```bash
# Change port in docker-compose.yml
ports:
  - "8081:80"  # Use 8081 instead of 8080
```

### Reset Everything

```bash
# Nuclear option: remove all containers, volumes, and images
docker-compose down -v
docker system prune -a --volumes
docker-compose up -d --build
```

---

## Further Reading

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Docker Hub Documentation](https://docs.docker.com/docker-hub/)
- [12-Factor App Methodology](https://12factor.net/)