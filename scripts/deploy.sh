#!/bin/bash
# JJ-Bot Deployment Script
# Handles deployment for development and production environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "=============================================="
    echo "  JJ-Bot Professional Trading Platform"
    echo "  Deployment Script"
    echo "=============================================="
    echo ""
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"
    else
        print_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi

    # Check pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 found"
    else
        print_error "pip3 not found"
        exit 1
    fi

    # Check Node.js (for frontend)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js found: $NODE_VERSION"
    else
        print_warning "Node.js not found. Frontend build will be skipped."
    fi

    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        print_success "Docker found"
        DOCKER_AVAILABLE=true
    else
        print_warning "Docker not found. Docker deployment unavailable."
        DOCKER_AVAILABLE=false
    fi

    echo ""
}

# Install Python dependencies
install_python_deps() {
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
    print_success "Python dependencies installed"
}

# Install frontend dependencies
install_frontend_deps() {
    if command -v node &> /dev/null; then
        echo "Installing frontend dependencies..."
        cd dashboard/jj-dashboard
        npm install
        cd ../..
        print_success "Frontend dependencies installed"
    fi
}

# Build frontend
build_frontend() {
    if command -v node &> /dev/null; then
        echo "Building frontend..."
        cd dashboard/jj-dashboard
        npm run build
        cd ../..
        print_success "Frontend built successfully"
    fi
}

# Generate SSL certificates
setup_ssl() {
    echo "Setting up SSL certificates..."
    python3 config/ssl_config.py generate --cn localhost --days 365
    print_success "SSL certificates generated"
}

# Initialize database
init_database() {
    echo "Initializing database..."
    mkdir -p data models backups logs
    print_success "Directories created"
}

# Run development server
run_dev() {
    print_header
    echo "Starting development server..."
    echo ""
    echo "API Server: http://127.0.0.1:8000"
    echo "Dashboard:  http://localhost:5173"
    echo "Swagger:    http://127.0.0.1:8000/docs"
    echo ""

    # Start API server in background
    python3 scripts/run_server.py --reload &
    API_PID=$!

    # Start frontend dev server
    if command -v node &> /dev/null; then
        cd dashboard/jj-dashboard
        npm run dev &
        FRONTEND_PID=$!
        cd ../..
    fi

    # Wait for interrupt
    trap "kill $API_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait
}

# Run production server
run_prod() {
    print_header
    echo "Starting production server..."

    # Check for HTTPS
    if [ -f "config/ssl/server.crt" ]; then
        echo "HTTPS enabled"
        python3 scripts/run_server.py --host 0.0.0.0 --port 8000 --https --workers 4
    else
        print_warning "SSL certificates not found. Running in HTTP mode."
        print_warning "Run './scripts/deploy.sh ssl' to generate certificates."
        python3 scripts/run_server.py --host 0.0.0.0 --port 8000 --workers 4
    fi
}

# Docker deployment
docker_deploy() {
    if [ "$DOCKER_AVAILABLE" != "true" ]; then
        print_error "Docker is not installed"
        exit 1
    fi

    print_header
    echo "Building and starting Docker containers..."

    docker-compose build
    docker-compose up -d

    print_success "Docker containers started"
    echo ""
    echo "API Server: http://localhost:8000"
    echo "Dashboard:  http://localhost:5173"
    echo ""
    echo "Run 'docker-compose logs -f' to view logs"
    echo "Run 'docker-compose down' to stop"
}

# Show help
show_help() {
    print_header
    echo "Usage: ./scripts/deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install     Install all dependencies"
    echo "  dev         Run development server"
    echo "  prod        Run production server"
    echo "  docker      Deploy with Docker"
    echo "  ssl         Generate SSL certificates"
    echo "  build       Build frontend for production"
    echo "  check       Check prerequisites"
    echo "  help        Show this help message"
    echo ""
}

# Main
case "${1:-help}" in
    install)
        check_prerequisites
        install_python_deps
        install_frontend_deps
        init_database
        print_success "Installation complete!"
        ;;
    dev)
        run_dev
        ;;
    prod)
        run_prod
        ;;
    docker)
        check_prerequisites
        docker_deploy
        ;;
    ssl)
        setup_ssl
        ;;
    build)
        build_frontend
        ;;
    check)
        check_prerequisites
        ;;
    help|*)
        show_help
        ;;
esac
