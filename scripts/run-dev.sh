#!/usr/bin/env bash
# This script requires tmux
# To enable mouse scrolling, create a file at ~/.tmux.conf with the following content:
# set -g mouse on

set -euo pipefail
cd "$(dirname "$0")/.." || return


# Check if tmux is installed
check_tmux_installed() {
    if ! command -v tmux &> /dev/null; then
        echo "tmux is not installed. Please install tmux to use this script."
        exit 1
    fi
}

# Kill an existing tmux session
kill_tmux_session() {
    tmux kill-session -t dev || true
}

# Start a new tmux session
start_tmux_session() {
    tmux new-session -d -s dev
}

# Start Tailwind in pane 0
run_tailwind() {
    tmux send-keys -t dev "rm -f ./app/web/html/static/css/tailwind-styles.css && npm run watch" C-m
}

# Start Uvicorn and setup in pane 1
run_uvicorn_and_setup() {
    tmux split-window -h -t dev
    tmux send-keys -t dev:0.1 "uv pip sync requirements-dev.txt" C-m
    # Make the left pane 1/3 window and right 2/3
    window_width=$(tmux display-message -p -t dev '#{window_width}')
    tmux resize-pane -t dev:0.0 -x "$((window_width / 3))"
    if [ "$START_POSTGRES" == "true" ]; then
        tmux send-keys -t dev:0.1 "docker start postgres" C-m
    fi
    tmux send-keys -t dev:0.1 "uvicorn 'app.web.main:create_app' --factory --host=0.0.0.0 --reload --reload-include='*.html' --reload-include='*.css' --reload-include='*.js'" C-m
}

# Start Browser Sync in pane 1 (optional)
run_browser_sync() {
    if [ "$BROWSER_SYNC" == "true" ]; then
        tmux split-window -v -t dev:0.0
        tmux send-keys -t dev:0.1 "browser-sync http://localhost:8000 app/web/html/static -w -f ." C-m
    fi
}

# Attach to tmux session
attach_tmux() {
    tmux attach -t dev
}

main() {
    check_tmux_installed
    kill_tmux_session
    start_tmux_session
    run_tailwind
    run_uvicorn_and_setup
    run_browser_sync
    attach_tmux
}

echo_usage() {
    echo 'Run the app locally in development mode.'
    echo
    echo 'This script requires tmux to be installed. `sudo apt-get install tmux`'
    echo
    echo 'OPTIONS:'
    echo '  --help             Display this help message and exit.'
    echo '  -b/-nb, --browser-sync/--no-browser-sync'
    echo '                     Start/Do not start Browser Sync. Default: --no-browser-sync.'
    echo '  -p/-np, --start-postgres/--no-start-postgres'
    echo '                     Start/Do not start Postgres. Default: --start-postgres.'
    echo '  --kill-tmux       Kill the existing tmux session and exit. Default: false.'
}

# Parse command line options
BROWSER_SYNC=false
START_POSTGRES=true

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -k|--kill-tmux) kill_tmux_session; exit 0 ;;
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
