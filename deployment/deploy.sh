#!/bin/bash

# Advanced Blockchain Dashboard Deployment Script
# This script deploys the complete dashboard system with all three microservices

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/ubuntu/Sandeep/projects/Gitintellisense"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
LOGS_DIR="$PROJECT_ROOT/logs"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        print_success "$service_name is running on port $port"
        return 0
    else
        print_error "$service_name is not running on port $port"
        return 1
    fi
}

# Function to wait for service to start
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to start on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_success "$service_name is now running on port $port"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt-get update -qq
    
    # Install required packages
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        redis-server \
        mongodb \
        nginx \
        nodejs \
        npm \
        lsof \
        curl \
        jq
    
    # Install PM2 globally
    sudo npm install -g pm2
    
    # Install Python dependencies
    cd "$PROJECT_ROOT"
    pip3 install --user \
        aiohttp \
        aiohttp-cors \
        aioredis \
        motor \
        pymongo \
        pyjwt \
        cryptography \
        requests \
        asyncio
    
    print_success "Dependencies installed successfully"
}

# Function to setup directories
setup_directories() {
    print_status "Setting up directories..."
    
    # Create logs directory
    mkdir -p "$LOGS_DIR"
    chmod 755 "$LOGS_DIR"
    
    # Create nginx error pages directory
    sudo mkdir -p /var/www/html
    
    # Create simple error pages
    sudo tee /var/www/html/404.html > /dev/null << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The requested page could not be found.</p>
    <a href="/">Return to Dashboard</a>
</body>
</html>
EOF

    sudo tee /var/www/html/50x.html > /dev/null << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Service Temporarily Unavailable</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Service Temporarily Unavailable</h1>
    <p>The service is temporarily unavailable. Please try again later.</p>
</body>
</html>
EOF
    
    print_success "Directories setup completed"
}

# Function to start services
start_services() {
    print_status "Starting system services..."
    
    # Start Redis
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    # Start MongoDB
    sudo systemctl start mongod
    sudo systemctl enable mongod
    
    print_success "System services started"
}

# Function to configure Nginx
configure_nginx() {
    print_status "Configuring Nginx..."
    
    # Backup existing nginx configuration
    if [ -f "$NGINX_SITES_AVAILABLE/blockchain-dashboard" ]; then
        sudo cp "$NGINX_SITES_AVAILABLE/blockchain-dashboard" "$NGINX_SITES_AVAILABLE/blockchain-dashboard.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Copy new configuration
    sudo cp "$DEPLOYMENT_DIR/nginx.conf" "$NGINX_SITES_AVAILABLE/blockchain-dashboard"
    
    # Enable the site
    sudo ln -sf "$NGINX_SITES_AVAILABLE/blockchain-dashboard" "$NGINX_SITES_ENABLED/blockchain-dashboard"
    
    # Test nginx configuration
    if sudo nginx -t; then
        print_success "Nginx configuration is valid"
        
        # Reload nginx
        sudo systemctl reload nginx
        print_success "Nginx reloaded successfully"
    else
        print_error "Nginx configuration test failed"
        return 1
    fi
}

# Function to deploy dashboard services
deploy_dashboard() {
    print_status "Deploying blockchain dashboard services..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing PM2 processes (if any)
    pm2 delete blockchain-dashboard-frontend blockchain-dashboard-middleware blockchain-dashboard-backend 2>/dev/null || true
    
    # Start services using PM2
    pm2 start "$DEPLOYMENT_DIR/pm2.ecosystem.config.js"
    
    # Save PM2 configuration
    pm2 save
    
    # Setup PM2 startup script
    pm2 startup systemd -u ubuntu --hp /home/ubuntu
    
    print_success "Dashboard services deployed"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for services to start
    sleep 10
    
    # Check each service
    local all_services_ok=true
    
    if ! wait_for_service "Frontend" 1201; then
        all_services_ok=false
    fi
    
    if ! wait_for_service "Middleware" 1202; then
        all_services_ok=false
    fi
    
    if ! wait_for_service "Backend" 1203; then
        all_services_ok=false
    fi
    
    # Check Nginx
    if ! check_service "Nginx" 80; then
        all_services_ok=false
    fi
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    
    if curl -s -f "http://localhost:1202/health" > /dev/null; then
        print_success "Middleware health check passed"
    else
        print_error "Middleware health check failed"
        all_services_ok=false
    fi
    
    if curl -s -f "http://localhost:1203/api/health" > /dev/null; then
        print_success "Backend health check passed"
    else
        print_error "Backend health check failed"
        all_services_ok=false
    fi
    
    # Test main dashboard
    if curl -s -f "http://localhost/" > /dev/null; then
        print_success "Frontend accessibility check passed"
    else
        print_error "Frontend accessibility check failed"
        all_services_ok=false
    fi
    
    if [ "$all_services_ok" = true ]; then
        print_success "All services are running correctly!"
        print_status "Dashboard is available at: http://3.111.22.56/"
        print_status "API Gateway: http://3.111.22.56/api/"
        print_status "WebSocket: ws://3.111.22.56/ws"
    else
        print_error "Some services failed to start properly"
        return 1
    fi
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    echo
    
    # PM2 status
    pm2 list
    echo
    
    # Port status
    print_status "Port Status:"
    echo "Frontend (1201): $(lsof -Pi :1201 -sTCP:LISTEN -t >/dev/null && echo 'RUNNING' || echo 'STOPPED')"
    echo "Middleware (1202): $(lsof -Pi :1202 -sTCP:LISTEN -t >/dev/null && echo 'RUNNING' || echo 'STOPPED')"
    echo "Backend (1203): $(lsof -Pi :1203 -sTCP:LISTEN -t >/dev/null && echo 'RUNNING' || echo 'STOPPED')"
    echo "Nginx (80): $(lsof -Pi :80 -sTCP:LISTEN -t >/dev/null && echo 'RUNNING' || echo 'STOPPED')"
    echo
    
    # System services
    print_status "System Services:"
    echo "Redis: $(systemctl is-active redis-server)"
    echo "MongoDB: $(systemctl is-active mongod)"
    echo "Nginx: $(systemctl is-active nginx)"
}

# Main deployment function
main() {
    print_status "🚀 Starting Advanced Blockchain Dashboard Deployment"
    print_status "=================================================="
    
    case "${1:-deploy}" in
        "install")
            install_dependencies
            ;;
        "setup")
            setup_directories
            start_services
            ;;
        "nginx")
            configure_nginx
            ;;
        "deploy")
            install_dependencies
            setup_directories
            start_services
            configure_nginx
            deploy_dashboard
            verify_deployment
            show_status
            ;;
        "status")
            show_status
            ;;
        "restart")
            pm2 restart all
            sudo systemctl reload nginx
            verify_deployment
            ;;
        "stop")
            pm2 stop all
            print_success "All services stopped"
            ;;
        "logs")
            pm2 logs
            ;;
        *)
            echo "Usage: $0 {install|setup|nginx|deploy|status|restart|stop|logs}"
            echo
            echo "Commands:"
            echo "  install  - Install system dependencies"
            echo "  setup    - Setup directories and start system services"
            echo "  nginx    - Configure Nginx"
            echo "  deploy   - Full deployment (default)"
            echo "  status   - Show service status"
            echo "  restart  - Restart all services"
            echo "  stop     - Stop all services"
            echo "  logs     - Show service logs"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
