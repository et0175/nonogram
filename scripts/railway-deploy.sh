#!/bin/bash

# Railway Deployment & Management Script
# Usage: ./scripts/railway-deploy.sh [command]

set -e

PROJECT_NAME="nonogram-admin"
COLORS='\033[0m\033[36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function print_header() {
    echo -e "${COLORS}════════════════════════════════════════${NC}"
    echo -e "${COLORS}$1${NC}"
    echo -e "${COLORS}════════════════════════════════════════${NC}"
}

function print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

function print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Railway CLI is installed
check_railway() {
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI not installed"
        echo "Install with: npm install -g @railway/cli"
        exit 1
    fi
    print_success "Railway CLI found"
}

# Check if logged in
check_login() {
    if railway status &> /dev/null; then
        print_success "Logged in to Railway"
    else
        print_warning "Not logged in - running: railway login"
        railway login
    fi
}

# Initialize project
cmd_init() {
    print_header "Initializing Railway Project"
    check_railway
    check_login

    if railway status &> /dev/null; then
        print_warning "Project already initialized"
    else
        railway init --name "$PROJECT_NAME"
        print_success "Project initialized"
    fi
}

# Deploy to Railway
cmd_deploy() {
    print_header "Deploying to Railway"
    check_railway
    check_login

    # Ensure code is committed
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Uncommitted changes detected"
        git add -A
        git commit -m "deploy: Railway deployment $(date +%s)"
        print_success "Changes committed"
    fi

    print_warning "Deploying... this may take 2-5 minutes"
    railway up

    print_success "Deployment complete!"
    print_header "Getting deployment info..."
    railway open
}

# View logs
cmd_logs() {
    print_header "Railway Logs (Press Ctrl+C to exit)"
    check_railway
    railway logs --follow
}

# Set environment variables
cmd_vars() {
    local key=$2
    local value=$3

    if [ -z "$key" ] || [ -z "$value" ]; then
        print_header "Environment Variables"
        railway variables list
    else
        print_header "Setting $key"
        railway variables set "$key" "$value"
        print_success "Set $key"
    fi
}

# Get deployment URL
cmd_url() {
    print_header "Deployment Information"
    railway open
    echo ""
    print_warning "Use 'railway domains' to see your app URL"
}

# Monitor deployment
cmd_monitor() {
    print_header "Deployment Status"
    railway status
    echo ""
    print_header "Recent Logs (last 20 lines)"
    railway logs --count 20
}

# Show help
cmd_help() {
    cat << 'HELP'

Railway Deployment Script
Usage: ./scripts/railway-deploy.sh [command]

Commands:
    init          Initialize Railway project (first time only)
    deploy        Deploy current code to Railway
    logs          View live deployment logs
    vars [K] [V]  List vars, or set KEY=VALUE
    url           Open Railway project dashboard
    monitor       Show deployment status & recent logs
    help          Show this help message

Examples:
    ./scripts/railway-deploy.sh init              # First time setup
    ./scripts/railway-deploy.sh deploy            # Deploy latest code
    ./scripts/railway-deploy.sh logs              # Watch logs in real-time
    ./scripts/railway-deploy.sh vars FLASK_ENV production
    ./scripts/railway-deploy.sh monitor           # Check health

Environment Variables (set via: vars KEY VALUE):
    FLASK_ENV           production|development
    SECRET_KEY          Your secret key (auto-generated)
    DATABASE_URL        PostgreSQL connection (optional)

Quick Start:
    1. ./scripts/railway-deploy.sh init
    2. ./scripts/railway-deploy.sh deploy
    3. ./scripts/railway-deploy.sh vars FLASK_ENV production
    4. ./scripts/railway-deploy.sh logs

HELP
}

# Main
main() {
    local cmd=${1:-help}

    case $cmd in
        init)
            cmd_init
            ;;
        deploy)
            cmd_deploy
            ;;
        logs)
            cmd_logs
            ;;
        vars)
            cmd_vars "$@"
            ;;
        url)
            cmd_url
            ;;
        monitor)
            cmd_monitor
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            print_error "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
