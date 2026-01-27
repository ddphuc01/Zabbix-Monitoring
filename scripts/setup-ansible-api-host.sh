#!/bin/bash
###############################################################################
# Ansible REST API Service - Host Setup Script
# 
# Purpose: Setup Ansible REST API service on host machine for Zabbix Monitoring
# Author: Zabbix Monitoring Team
# Date: 2026-01-27
#
# Requirements:
#   - Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / CentOS 8+
#   - Python 3.8+
#   - Root/sudo access
#   - Port 5001 available
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$PROJECT_ROOT/ansible-api-service"
SYSTEMD_SERVICE="ansible-api.service"
SERVICE_PORT=5001

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
    log_success "Running as root"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_info "Detected OS: $OS $OS_VERSION"
    else
        log_error "Cannot detect OS. /etc/os-release not found"
        exit 1
    fi
}

# Check Python version
check_python() {
    log_info "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        log_info "Please install Python 3.8+ first"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        log_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    log_success "Python version: $PYTHON_VERSION ✓"
}

# Check port availability
check_port() {
    log_info "Checking if port $SERVICE_PORT is available..."
    
    if netstat -tuln 2>/dev/null | grep -q ":$SERVICE_PORT "; then
        log_error "Port $SERVICE_PORT is already in use"
        log_info "Please stop the service using this port or change SERVICE_PORT"
        netstat -tuln | grep ":$SERVICE_PORT"
        exit 1
    fi
    
    log_success "Port $SERVICE_PORT is available ✓"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y -qq \
                python3-pip \
                python3-venv \
                ansible \
                openssh-client \
                curl \
                net-tools
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y -q \
                python3-pip \
                ansible \
                openssh-clients \
                curl \
                net-tools
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed ✓"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    cd "$SERVICE_DIR"
    
    # Determine pip install flags based on OS version
    PIP_FLAGS="-q"
    
    # Ubuntu 24.04+ and Debian 12+ use PEP 668 (externally-managed-environment)
    # Need to use --break-system-packages flag
    if [[ "$OS" == "ubuntu" && "${OS_VERSION%%.*}" -ge 24 ]] || \
       [[ "$OS" == "debian" && "${OS_VERSION%%.*}" -ge 12 ]]; then
        log_warning "Ubuntu 24.04+ / Debian 12+ detected - using --break-system-packages flag"
        PIP_FLAGS="$PIP_FLAGS --break-system-packages"
    fi
    
    # Upgrade pip
    python3 -m pip install --upgrade pip $PIP_FLAGS 2>/dev/null || true
    
    # Install from requirements.txt
    if [ -f requirements.txt ]; then
        python3 -m pip install -r requirements.txt $PIP_FLAGS
        log_success "Python dependencies installed from requirements.txt ✓"
    else
        log_warning "requirements.txt not found, installing manually..."
        python3 -m pip install fastapi uvicorn ansible-runner pydantic requests $PIP_FLAGS
        log_success "Python dependencies installed manually ✓"
    fi
}

# Setup systemd service
setup_systemd() {
    log_info "Setting up systemd service..."
    
    # Copy service file
    if [ -f "$SERVICE_DIR/systemd/$SYSTEMD_SERVICE" ]; then
        cp "$SERVICE_DIR/systemd/$SYSTEMD_SERVICE" /etc/systemd/system/
        log_success "Service file copied to /etc/systemd/system/"
    else
        log_error "Service file not found: $SERVICE_DIR/systemd/$SYSTEMD_SERVICE"
        exit 1
    fi
    
    # Reload systemd
    systemctl daemon-reload
    log_success "Systemd daemon reloaded ✓"
    
    # Enable service
    systemctl enable $SYSTEMD_SERVICE
    log_success "Service enabled (will start on boot) ✓"
    
    # Start service
    systemctl start $SYSTEMD_SERVICE
    log_success "Service started ✓"
    
    # Wait for service to be ready
    sleep 3
    
    # Check status
    if systemctl is-active --quiet $SYSTEMD_SERVICE; then
        log_success "Service is running ✓"
    else
        log_error "Service failed to start"
        log_info "Checking logs..."
        journalctl -u $SYSTEMD_SERVICE -n 20 --no-pager
        exit 1
    fi
}

# Test API endpoint
test_api() {
    log_info "Testing API endpoint..."
    
    # Test health endpoint
    if curl -s -f http://localhost:$SERVICE_PORT/health > /dev/null; then
        log_success "Health endpoint is responding ✓"
        
        # Show health response
        HEALTH_RESPONSE=$(curl -s http://localhost:$SERVICE_PORT/health | python3 -m json.tool)
        echo "$HEALTH_RESPONSE"
    else
        log_error "Health endpoint is not responding"
        log_info "Checking logs..."
        journalctl -u $SYSTEMD_SERVICE -n 20 --no-pager
        exit 1
    fi
}

# Verify Ansible connectivity
verify_ansible() {
    log_info "Verifying Ansible setup..."
    
    # Check ansible command
    if command -v ansible &> /dev/null; then
        ANSIBLE_VERSION=$(ansible --version | head -n1)
        log_success "Ansible: $ANSIBLE_VERSION ✓"
    else
        log_warning "Ansible command not found in PATH"
    fi
    
    # Check inventory file
    INVENTORY_FILE="$PROJECT_ROOT/ansible/inventory/hosts.yml"
    if [ -f "$INVENTORY_FILE" ]; then
        log_success "Inventory file found: $INVENTORY_FILE ✓"
    else
        log_warning "Inventory file not found: $INVENTORY_FILE"
        log_info "Please create inventory file before running diagnostics"
    fi
}

# Display summary
show_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Ansible REST API Service - READY!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Service Status:  ${GREEN}RUNNING${NC}"
    echo -e "Service Port:    ${BLUE}$SERVICE_PORT${NC}"
    echo -e "API Endpoint:    ${BLUE}http://localhost:$SERVICE_PORT${NC}"
    echo -e "Health Check:    ${BLUE}http://localhost:$SERVICE_PORT/health${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  Check status:   ${BLUE}sudo systemctl status $SYSTEMD_SERVICE${NC}"
    echo -e "  View logs:      ${BLUE}sudo journalctl -u $SYSTEMD_SERVICE -f${NC}"
    echo -e "  Restart:        ${BLUE}sudo systemctl restart $SYSTEMD_SERVICE${NC}"
    echo -e "  Stop:           ${BLUE}sudo systemctl stop $SYSTEMD_SERVICE${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Update docker-compose.yml if not already done"
    echo -e "  2. Restart Docker stack: ${BLUE}docker-compose down && docker-compose up -d${NC}"
    echo -e "  3. Test from container: ${BLUE}docker exec -it zabbix-ai-webhook curl http://host.docker.internal:5001/health${NC}"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Ansible REST API Service Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_root
    detect_os
    check_python
    check_port
    install_dependencies
    install_python_deps
    setup_systemd
    test_api
    verify_ansible
    show_summary
    
    log_success "Setup completed successfully! 🚀"
}

# Run main function
main "$@"
