#!/bin/zsh

# Local Development Server Management Script
# Manages PHP development server and MariaDB for local website development

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_PORT=8080
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR=""
LOG_DIR=""
LEGACY_WWW_DIR=""
ROUTER_PATH=""
WEB_ROOT=""

# Optional overrides (CLI: --port/-p, --root/-r, --webroot/-w, env: DEVSERVER_PORT/DEVSERVER_ROOT/DEVSERVER_WEBROOT)
PHP_PORT="${DEVSERVER_PORT:-$DEFAULT_PORT}"
API_CHECK="${DEVSERVER_API_CHECK:-0}"
DB_CHECK="${DEVSERVER_DB_CHECK:-0}"
WEB_ROOT="${DEVSERVER_WEBROOT:-}"
PHP_LOG=""
PHP_PID_FILE=""

choose_default_webroot() {
    local default_root="$ROOT_DIR/public_html/www"
    local alternate_root="$ROOT_DIR/www.henseler.de"

    if [ -n "$WEB_ROOT" ]; then
        SERVER_DIR="$WEB_ROOT"
        return
    fi

    if [ -f "$default_root/index.html" ]; then
        SERVER_DIR="$default_root"
        return
    fi

    if [ -d "$alternate_root" ]; then
        SERVER_DIR="$alternate_root"
        return
    fi

    SERVER_DIR="$default_root"
}

set_root_paths() {
    choose_default_webroot
    if [ -d "$ROOT_DIR/logs" ]; then
        LOG_DIR="$ROOT_DIR/logs"
    else
        LOG_DIR="$SERVER_DIR/logs"
    fi
    LEGACY_WWW_DIR="$ROOT_DIR/www"
    ROUTER_PATH="$ROOT_DIR/.devserver/router.php"
}

update_port_paths() {
    PHP_LOG="$LOG_DIR/server/current/php-server-$PHP_PORT.log"
    PHP_PID_FILE="$LOG_DIR/php-server-$PHP_PORT.pid"
}

get_pids_on_port() {
    lsof -ti:$PHP_PORT 2>/dev/null | tr '\n' ' '
}

get_first_pid_on_port() {
    lsof -ti:$PHP_PORT 2>/dev/null | head -n 1
}

get_port_command() {
    lsof -iTCP:$PHP_PORT -sTCP:LISTEN -F c 2>/dev/null | sed -n 's/^c//p' | head -n 1
}

list_other_tenants() {
    setopt local_options null_glob
    local found=0
    for pidfile in "$LOG_DIR"/php-server-*.pid; do
        [ -e "$pidfile" ] || continue
        local filename
        filename="$(basename "$pidfile")"
        local port="${filename#php-server-}"
        port="${port%.pid}"
        if [ "$port" = "$PHP_PORT" ]; then
            continue
        fi
        local pid
        pid="$(cat "$pidfile" 2>/dev/null)"
        local status="stopped"
        if lsof -ti:$port >/dev/null 2>&1; then
            status="running"
        fi
        echo "  └─ Port: $port | PID: ${pid:-unknown} | Status: $status"
        found=1
    done
    if [ $found -eq 1 ]; then
        return 0
    fi
    return 1
}

set_root_paths

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"
update_port_paths
if [ -d "$LEGACY_WWW_DIR" ]; then
    print_warning "Legacy folder detected (unused): $LEGACY_WWW_DIR"
fi

# Function to print colored messages
print_success() { echo "${GREEN}✓${NC} $1" }
print_error() { echo "${RED}✗${NC} $1" }
print_warning() { echo "${YELLOW}⚠${NC} $1" }
print_info() { echo "${BLUE}ℹ${NC} $1" }

# Function to check if PHP server is running
is_php_running() {
    [ -n "$(get_pids_on_port)" ]
    return $?
}

# Function to check if MariaDB is running
is_mariadb_running() {
    brew services list | grep mariadb | grep started > /dev/null 2>&1
    return $?
}

# Function to start PHP server
start_php() {
    # Clean up stale PID file if exists but process is not running
    if [ -f "$PHP_PID_FILE" ] && ! is_php_running; then
        print_warning "Cleaning up stale PID file..."
        rm -f "$PHP_PID_FILE"
    fi

    PORT_PIDS="$(get_pids_on_port)"
    if [ -n "$PORT_PIDS" ]; then
        if [ -f "$PHP_PID_FILE" ]; then
            PID=$(cat "$PHP_PID_FILE")
            if echo "$PORT_PIDS" | grep -q "\b$PID\b"; then
                print_warning "PHP server is already running on port $PHP_PORT"
                print_info "Existing process PID: $PID"
                return 0
            fi
        fi
        if [ "$(get_port_command)" = "php" ]; then
            PID="$(get_first_pid_on_port)"
            print_warning "Port $PHP_PORT is in use by unmanaged PHP process (PID: $PID)"
            print_info "Adopting PID and skipping start"
            echo "$PID" > "$PHP_PID_FILE"
            return 0
        fi
        print_error "Port $PHP_PORT is in use by another process (PID(s): $PORT_PIDS)"
        print_info "Refusing to start to avoid taking over another tenant"
        return 1
    fi

    # Verify router exists
    if [ ! -f "$ROUTER_PATH" ]; then
        print_error "Router file not found: $ROUTER_PATH"
        print_info "Server cannot start without router.php for proper API routing"
        return 1
    fi

    print_info "Starting PHP development server with router..."
    cd "$SERVER_DIR"

    # Create log directory if needed
    mkdir -p "$(dirname "$PHP_LOG")"

    # Start PHP server with router in background and save PID
    DEVSERVER_WEBROOT="$SERVER_DIR" nohup /usr/local/bin/php -S localhost:$PHP_PORT "$ROUTER_PATH" > "$PHP_LOG" 2>&1 &
    echo $! > "$PHP_PID_FILE"

    sleep 3

    if is_php_running; then
        print_success "PHP server started on http://localhost:$PHP_PORT"
        print_info "Logs: $PHP_LOG"
        print_warning "Note: Clear browser cache (Cmd+Shift+R) to see latest changes"
        return 0
    else
        print_error "Failed to start PHP server"
        print_info "Check logs at: $PHP_LOG"
        return 1
    fi
}

# Function to stop PHP server
stop_php() {
    PORT_PIDS="$(get_pids_on_port)"
    if [ -z "$PORT_PIDS" ]; then
        print_warning "PHP server is not running"
        # Clean up stale PID file if exists
        if [ -f "$PHP_PID_FILE" ]; then
            rm -f "$PHP_PID_FILE"
        fi
        return 0
    fi

    # If port is in use but we don't own the PID, do not stop it.
    if [ ! -f "$PHP_PID_FILE" ]; then
        if [ "$(get_port_command)" = "php" ]; then
            PID="$(get_first_pid_on_port)"
            print_warning "Adopting unmanaged PHP process on port $PHP_PORT (PID: $PID)"
            echo "$PID" > "$PHP_PID_FILE"
        else
            print_warning "Port $PHP_PORT is in use by another process (PID(s): $PORT_PIDS)"
            print_info "No PID file for this tenant, refusing to stop"
            return 1
        fi
    fi

    print_info "Stopping PHP server..."
    PID=$(cat "$PHP_PID_FILE")
    if kill -9 "$PID" 2>/dev/null; then
        print_info "Killed process from PID file: $PID"
    else
        print_warning "Failed to kill PID from PID file: $PID"
    fi
    rm -f "$PHP_PID_FILE"

    sleep 1

    PORT_PIDS="$(get_pids_on_port)"
    if [ -z "$PORT_PIDS" ]; then
        print_success "PHP server stopped"
        return 0
    else
        print_warning "Port $PHP_PORT is still in use by PID(s): $PORT_PIDS"
        print_info "Not stopping other tenants"
        return 1
    fi
}

# Function to start MariaDB
start_mariadb() {
    if is_mariadb_running; then
        print_warning "MariaDB is already running"
        return 0
    fi

    print_info "Starting MariaDB..."
    brew services start mariadb > /dev/null 2>&1

    sleep 3

    if is_mariadb_running; then
        print_success "MariaDB started"
        return 0
    else
        print_error "Failed to start MariaDB"
        return 1
    fi
}

# Function to stop MariaDB
stop_mariadb() {
    if ! is_mariadb_running; then
        print_warning "MariaDB is not running"
        return 0
    fi

    print_info "Stopping MariaDB..."
    brew services stop mariadb > /dev/null 2>&1

    sleep 2

    if ! is_mariadb_running; then
        print_success "MariaDB stopped"
        return 0
    else
        print_error "Failed to stop MariaDB"
        return 1
    fi
}

# Function to show status
show_status() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Local Development Server Status${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""

    # PHP Server Status
    if is_php_running; then
        PID="$(get_pids_on_port)"
        print_success "PHP Server: Running (PID: $PID)"
        echo "  └─ URL: ${GREEN}http://localhost:$PHP_PORT${NC}"
        echo "  └─ Logs: $PHP_LOG"
    else
        print_error "PHP Server: Stopped"
    fi

    echo ""
    echo "${BLUE}Other Tenants${NC}"
    if list_other_tenants; then
        :
    else
        print_info "No other tenant PID files found"
    fi
    echo ""

    # MariaDB Status (optional)
    if [ "$DB_CHECK" = "1" ]; then
        if is_mariadb_running; then
            print_success "MariaDB: Running"
            echo "  └─ Port: 3306"
            echo "  └─ Database: roblemumin_db"
        else
            print_error "MariaDB: Stopped"
        fi
    else
        print_info "MariaDB: Check skipped (use --db-check to enable)"
    fi

    echo ""

    # Test API connection if enabled
    if [ "$API_CHECK" = "1" ] && is_php_running; then
        echo "${BLUE}Testing API Connection...${NC}"
        HTTP_CODE=$(curl -s --connect-timeout 2 --max-time 4 -o /dev/null -w "%{http_code}" http://localhost:$PHP_PORT/api/status)
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "API Status: Connected (HTTP $HTTP_CODE)"
            echo "  └─ Test: ${GREEN}http://localhost:$PHP_PORT/api/status${NC}"
        else
            print_warning "API Status: HTTP $HTTP_CODE (check API logs)"
        fi
    fi

    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
}

show_status_php() {
    echo ""
    echo "${BLUE}PHP Server Status${NC}"
    if is_php_running; then
        PID="$(get_pids_on_port)"
        print_success "Running (PID: $PID)"
        echo "  └─ URL: ${GREEN}http://localhost:$PHP_PORT${NC}"
        echo "  └─ Logs: $PHP_LOG"
    else
        print_error "Stopped"
    fi
    echo ""
}

show_status_tenants() {
    echo ""
    echo "${BLUE}Other Tenants${NC}"
    if list_other_tenants; then
        :
    else
        print_info "No other tenant PID files found"
    fi
    echo ""
}

show_status_db() {
    echo ""
    echo "${BLUE}MariaDB Status${NC}"
    if is_mariadb_running; then
        print_success "Running"
        echo "  └─ Port: 3306"
        echo "  └─ Database: roblemumin_db"
    else
        print_error "Stopped"
    fi
    echo ""
}

show_status_api() {
    echo ""
    echo "${BLUE}API Status${NC}"
    if is_php_running; then
        HTTP_CODE=$(curl -s --connect-timeout 2 --max-time 4 -o /dev/null -w "%{http_code}" http://localhost:$PHP_PORT/api/status)
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "Connected (HTTP $HTTP_CODE)"
            echo "  └─ Test: ${GREEN}http://localhost:$PHP_PORT/api/status${NC}"
        else
            print_warning "HTTP $HTTP_CODE (check API logs)"
        fi
    else
        print_warning "PHP server is not running"
    fi
    echo ""
}

show_menu() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Development Server Menu${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    echo "1) Start all"
    echo "2) Stop all"
    echo "3) Restart PHP only"
    echo "4) Start PHP only"
    echo "5) Stop PHP only"
    echo "6) Start DB only"
    echo "7) Stop DB only"
    echo "8) Restart DB only"
    echo "9) Status (full)"
    echo "10) Status (PHP)"
    echo "11) Status (DB)"
    echo "12) Status (API)"
    echo "13) Status (Other tenants)"
    echo "14) Logs"
    echo "0) Exit"
    echo ""
    echo -n "Select an option: "
    read -r choice
    case "$choice" in
        1) start_all ;;
        2) stop_all ;;
        3) restart_php_only ;;
        4) start_php_only ;;
        5) stop_php_only ;;
        6) start_db_only ;;
        7) stop_db_only ;;
        8) restart_db_only ;;
        9) show_status ;;
        10) show_status_php ;;
        11) show_status_db ;;
        12) show_status_api ;;
        13) show_status_tenants ;;
        14) show_logs ;;
        0) exit 0 ;;
        *) print_warning "Invalid option" ;;
    esac
}

# Function to start all services
start_all() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Starting Development Environment${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""

    start_mariadb
    sleep 1
    start_php

    echo ""
    print_success "Development environment ready!"
    echo ""
    print_info "Access your site at: ${GREEN}http://localhost:$PHP_PORT${NC}"
    print_info "Library page: ${GREEN}http://localhost:$PHP_PORT/library.html${NC}"
    echo ""
}

# Function to stop all services
stop_all() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Stopping Development Environment${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""

    stop_php
    sleep 1
    stop_mariadb

    echo ""
    print_success "Development environment stopped"
    echo ""
}

# Function to start only PHP server
start_php_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Starting PHP Server Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    start_php
    echo ""
}

# Function to start only MariaDB
start_db_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Starting MariaDB Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    start_mariadb
    echo ""
}

# Function to stop only PHP server
stop_php_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Stopping PHP Server Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    stop_php
    echo ""
}

# Function to stop only MariaDB
stop_db_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Stopping MariaDB Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    stop_mariadb
    echo ""
}

# Placeholder API management (extend when API service exists)
start_api() {
    print_warning "API service not configured in this project"
    return 1
}

stop_api() {
    print_warning "API service not configured in this project"
    return 1
}

restart_api() {
    print_warning "API service not configured in this project"
    return 1
}

# Function to restart all services
restart_all() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Restarting Development Environment${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""

    stop_php
    sleep 2
    start_php

    echo ""
    print_success "Development environment restarted!"
    echo ""
}

# Function to restart only PHP server
restart_php_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Restarting PHP Server Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    stop_php
    sleep 2
    start_php
    echo ""
}

# Function to restart only MariaDB
restart_db_only() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Restarting MariaDB Only${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    stop_mariadb
    sleep 2
    start_mariadb
    echo ""
}

# Function to show logs
show_logs() {
    if [ ! -f "$PHP_LOG" ]; then
        print_warning "No PHP server logs found"
        return
    fi

    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   PHP Server Logs (last 30 lines)${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    tail -30 "$PHP_LOG"
    echo ""
}

# Function to show help
show_help() {
    echo ""
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo "${BLUE}   Development Server Manager${NC}"
    echo "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    echo "Usage: ./devserver.sh [command] [--port|-p PORT] [--root|-r PATH] [--webroot|-w PATH] [--api-check|--no-api-check] [--db-check|--no-db-check]"
    echo ""
    echo "Commands:"
    echo "  ${GREEN}start${NC}          Start PHP server and MariaDB"
    echo "  ${GREEN}stop${NC}           Stop PHP server and MariaDB"
    echo "  ${GREEN}restart${NC}        Restart PHP server only (safe for multi-tenant)"
    echo "  ${GREEN}start-php${NC}      Start only PHP server"
    echo "  ${GREEN}stop-php${NC}       Stop only PHP server"
    echo "  ${GREEN}restart-php${NC}    Restart only PHP server"
    echo "  ${GREEN}start-db${NC}       Start only MariaDB"
    echo "  ${GREEN}stop-db${NC}        Stop only MariaDB"
    echo "  ${GREEN}restart-db${NC}     Restart only MariaDB"
    echo "  ${GREEN}start-api${NC}      Start only API service (if configured)"
    echo "  ${GREEN}stop-api${NC}       Stop only API service (if configured)"
    echo "  ${GREEN}restart-api${NC}    Restart only API service (if configured)"
    echo "  ${GREEN}menu${NC}           Open interactive menu"
    echo "  ${GREEN}status${NC}     Show status of all services"
    echo "  ${GREEN}logs${NC}       Show PHP server logs"
    echo "  ${GREEN}help${NC}       Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./devserver.sh start"
    echo "  ./devserver.sh start --port 8090"
    echo "  DEVSERVER_PORT=8090 ./devserver.sh start"
    echo "  ./devserver.sh status --root /Users/roble/Documents/henseler.de --webroot /Users/roble/Documents/henseler.de/www.henseler.de --port 8090"
    echo "  ./devserver.sh status --api-check --db-check"
    echo "  ./devserver.sh menu"
    echo "  ./devserver.sh restart-php --port 8080"
    echo "  ./devserver.sh restart-db"
    echo "  ./devserver.sh status"
    echo "  ./devserver.sh stop"
    echo ""
}

PORT_ARG=""
ROOT_ARG=""
WEB_ROOT_ARG=""
API_CHECK_ARG=""
DB_CHECK_ARG=""
CMD=""
while [ $# -gt 0 ]; do
    case "$1" in
        --api-check)
            API_CHECK_ARG="1"
            ;;
        --no-api-check)
            API_CHECK_ARG="0"
            ;;
        --db-check)
            DB_CHECK_ARG="1"
            ;;
        --no-db-check)
            DB_CHECK_ARG="0"
            ;;
        --webroot|-w)
            shift
            WEB_ROOT_ARG="$1"
            ;;
        --root|-r)
            shift
            ROOT_ARG="$1"
            ;;
        --port|-p)
            shift
            PORT_ARG="$1"
            ;;
        start|stop|restart|status|logs|help|--help|-h|start-php|stop-php|restart-php|start-db|stop-db|restart-db|start-api|stop-api|restart-api|menu)
            CMD="$1"
            ;;
        *)
            if [ -z "$CMD" ]; then
                CMD="$1"
            fi
            ;;
    esac
    shift
done

if [ -n "$PORT_ARG" ]; then
    PHP_PORT="$PORT_ARG"
fi
if [ -n "$API_CHECK_ARG" ]; then
    API_CHECK="$API_CHECK_ARG"
fi
if [ -n "$DB_CHECK_ARG" ]; then
    DB_CHECK="$DB_CHECK_ARG"
fi
if [ -n "$ROOT_ARG" ]; then
    ROOT_DIR="$ROOT_ARG"
fi
if [ -n "${DEVSERVER_ROOT:-}" ] && [ -z "$ROOT_ARG" ]; then
    ROOT_DIR="$DEVSERVER_ROOT"
fi
if [ -n "$WEB_ROOT_ARG" ]; then
    WEB_ROOT="$WEB_ROOT_ARG"
fi
set_root_paths
update_port_paths

# Main script logic
case "${CMD:-menu}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    start-php)
        start_php_only
        ;;
    stop-php)
        stop_php_only
        ;;
    restart-php)
        restart_php_only
        ;;
    start-db)
        start_db_only
        ;;
    stop-db)
        stop_db_only
        ;;
    restart-db)
        restart_db_only
        ;;
    start-api)
        start_api
        ;;
    stop-api)
        stop_api
        ;;
    restart-api)
        restart_api
        ;;
    menu)
        show_menu
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

exit 0
