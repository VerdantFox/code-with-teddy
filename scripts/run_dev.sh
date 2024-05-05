#!/usr/bin/env bash
# This script requires xdotool to be installed
# sudo apt-get install xdotool

set -euo pipefail
cd "$(dirname "$0")/.." || return

main() {
    run_setup
    run_tailwind
    run_browser_sync
    run_uvicorn
}

echo_usage() {
    echo 'Run the app locally in development mode.'
    echo
    # shellcheck disable=SC2016
    echo 'This script requires xdotool to be installed. `sudo apt-get install xdotool`'
    echo
    echo 'OPTIONS:'
    echo '  --help             Display this help message and exit.'
    echo '  -b/-nb, --browser-sync/--no-browser-sync'
    echo '                     Start/Do not start Browser Sync. Default: --no-browser-sync.'
    echo '  -p/-np, --start-postgres/--no-start-postgres'
    echo '                     Start/Do not start Postgres. Default: --start-postgres.'
}

# Helper function to open a new terminal (assuming GNOME Terminal)
open_new_terminal() {
    xdotool key 'ctrl+shift+grave'
    sleep 0.1
    xdotool getactivewindow windowfocus
    sleep 0.1
}

run_cmd() {
    xdotool type "$1"
    sleep 0.1
    xdotool key 'Return'
}

# Function to start Tailwind
run_tailwind() {
    open_new_terminal
    run_cmd "rm -f ./app/web/html/static/css/tailwind-styles.css"
    run_cmd "npm run watch"
}

# Function to start Uvicorn with optional Postgres
run_uvicorn() {
    open_new_terminal
    run_cmd 'uvicorn "app.web.main:create_app" --factory --host=0.0.0.0 --reload --reload-include="*.html" --reload-include="*.css" --reload-include="*.js"'
}

# Setup function including Postgres option
run_setup() {
    run_cmd 'uv pip sync requirements-dev.txt'
    if [ $START_POSTGRES == "true" ]; then
        run_cmd 'docker start postgres'
    fi
}

# Function to start Browser Sync
run_browser_sync() {
    if [ "$BROWSER_SYNC" == "true" ]; then
        open_new_terminal
        run_cmd 'browser-sync http://localhost:8000 app/web/html/static -w -f .'
    fi
}

# Parse command line options
BROWSER_SYNC=false
START_POSTGRES=true

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -b|--browser-sync) BROWSER_SYNC=true ;;
        -nb|--no-browser-sync) BROWSER_SYNC=false ;;
        -p|--start-postgres) START_POSTGRES=true ;;
        -np|--no-start-postgres) START_POSTGRES=false ;;
        --help) echo_usage; exit 0 ;;
        *) echo "Unknown parameter: $1"; echo_usage; exit 1 ;;
    esac
    shift
done

# Main execution logic
main
