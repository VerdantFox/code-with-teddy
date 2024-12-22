#!/usr/bin/env bash
# This script is used to deploy the application and services with docker-compose.
# The script can be run in development mode or production mode. Defaults to development mode.
#
# This script performs the following actions:
#   - Fetches and rebases the latest release-branch from github (for production run)
#   - Updates the crontab (for production run)
#   - Builds the docker images
#   - Stops the running containers
#   - Starts the containers with the new images
#   - Establishes logging
#   - Prunes dangling images and builds
#
# When writing crontab lines, append
# '>> "$(pwd)/logs/$(date +"%Y-%m-%d")_crontab.log"  2>&1'
# to commands to log output to a log file

# shellcheck disable=SC1091

set -euo pipefail
cd "$(dirname "$0")/.." || return


# ---------------------------------------------------------------------------
# GLOBALS
# ---------------------------------------------------------------------------
NODE_VERSION=22

#OPTS
DEBUG=${DEBUG:-0}
PROD=${PROD:-0}
BUILD=${BUILD:-1}
STOP=${STOP:-0}
START=${START:-1}
FROM_SCRATCH=${FROM_SCRATCH:-0}
IF_NEEDED=${IF_NEEDED:-0}

# crontab can't find docker compose without PATH defined
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
# Needed for correct timezone with 'date' calls
export TZ=America/Denver
# Log files
DATE="$(date +"%Y-%m-%d")"
CRON_LOG="$(pwd)/logs/${DATE}_crontab.log"
NGINX_LOG="$(pwd)/logs/${DATE}_nginx.log"
CERTBOT_LOG="$(pwd)/logs/${DATE}_certbot.log"
WEB_APP_LOG="$(pwd)/logs/${DATE}_web_app.log"
DB_LOG="$(pwd)/logs/${DATE}_db.log"
MIGRATION_LOG="$(pwd)/logs/${DATE}_migration.log"


# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------
# Echo how to use this script
echo_usage() {
    echo 'Build and deploy or tear-down app and service containers.'
    echo 'By default, (re-)builds and deploys containers in development mode.'
    echo
    echo 'OPTIONS:'
    echo '  --help            Display this help message and exit.'
    echo '  --debug           Announce global variables.'
    echo '  --dev/--prod      Deploy in development or production mode (default=dev).'
    echo '  --down            Tear down containers/network without (re-)starting.'
    echo '  --restart         Restart containers even if not re-built.'
    echo '  --skip-build      Skip the build step.'
    echo '  --from-scratch    (Re-)build containers from scratch without cache.'
    echo '  --if-needed       Only re-build/re-start if the release-branch has been updated. Only effects PROD=1.'
}

# Log message to stdout with timestamp and log level
log() {
    level="$1"
    message="$2"
    echo "$(date "+%Y-%m-%d %H:%M:%S,%3N") [deploy.sh] [$level] $message"
}

# Load environment variables
# Priority: actual environment variables > .env > .env.local
source_environment() {
    globals=$(printenv | grep '^DEBUG=\|^PROD=\|^BUILD=\|^STOP=\|^START=\|^FROM_SCRATCH=\|^IF_NEEDED=' || true)
    source .env.local
    touch .env
    source .env
    eval "${globals}"
}

# Announce global variables
announce_vars() {
    if [ "${DEBUG:-}" != "1" ]; then return; fi
    log DEBUG "Global variables set:"
    log DEBUG "DEBUG=${DEBUG:-}"
    log DEBUG "PROD=${PROD:-}"
    log DEBUG "BUILD=${BUILD:-}"
    log DEBUG "STOP=${STOP:-}"
    log DEBUG "START=${START:-}"
    log DEBUG "FROM_SCRATCH=${FROM_SCRATCH:-}"
    log DEBUG "IF_NEEDED=${IF_NEEDED:-}"
}

# Checkout and update the release branch (in production)
update_branch() {
    if [ "${PROD:-}" != "1" ]; then return; fi
    log INFO "Rebasing latest release-branch..."
    git fetch origin --prune
    checkout_result="$(git checkout release-branch)"
    log INFO "$checkout_result"
    if [[ "$checkout_result" == *"Your branch is up to date with 'origin/release-branch'."* && "${IF_NEEDED:-}" == "1" ]]
    then
        # Nothing to do then.
        exit 0
    fi
    git stash
    git pull
}

# Install crontab (in production)
# Can use `crontab -l` to check if the crontab exists and `crontab -r` to remove the crontab.
# Crontab has 3 jobs:
# - Every 5 minutes run this deploy script, only if the 'release-branch' has changed
# - 1x per day run this deploy script to rebuild the docker images from scratch (to get latest security patches)
# - 1x per day delete > 4-day old logs from the 'logs/' directory
install_crontab() {
    if [ "${PROD:-}" != "1" ]; then return; fi
    # Set up log for crontab jobs (including deployment log)
    mkdir -p "$(pwd)/logs"
    touch "$CRON_LOG"
    log INFO "Installing new crontab..."
crontab << ENDCRON
# Scheduled tasks
# This crontab was generated automatically by scripts/deploy.sh and should not be edited here.
# Times calculated for UTC. (America/Denver is UTC-7, so 12:00AM MST is 7:00AM UTC.)
# Deploy (building from scratch) and restart all containers: every day at 7:07AM UTC (12:07AM MST).
7 7 * * * PATH=$PATH TZ=America/Denver "$(pwd)/scripts/deploy.sh" --from-scratch --restart --prod >> "$CRON_LOG"  2>&1
# Deploy (only if needed): every 5 minutes.
*/5 * * * * PATH=$PATH TZ=America/Denver "$(pwd)/scripts/deploy.sh" --if-needed --prod >> "$CRON_LOG"  2>&1
# Remove 4-day-old logs (logs > 3 days old): every day at 7:37AM UTC (12:37AM MST).
37 7 * * * find "$(pwd)/logs/" -mtime +3  -exec rm {} \; >> "$CRON_LOG"  2>&1
ENDCRON
}

# Set docker-compose profile based on dev or prod
set_profile() {
    if [ "${PROD:-}" == "1" ]
    then
        PROFILE="prod"
    else
        PROFILE="dev"
    fi
}

# Set docker compose definitions and any extra build args
set_extras() {
    if [[ "${FROM_SCRATCH:-}" == "1" ]]
    then
        BUILD_EXTRAS=( "--no-cache" "--pull" )
    else
        unset BUILD_EXTRAS
    fi
    COMPOSE_EXTRAS=( "--file=docker_config/docker-compose.yaml" "--project-directory=." )
}

# Build the docker images
build_images() {
    if [ "${BUILD:-}" != "1" ]; then return; fi
    log INFO "Building latest images..."
    # shellcheck disable=SC2068
    docker compose ${COMPOSE_EXTRAS[@]:-} --profile $PROFILE build ${BUILD_EXTRAS[@]:-}
}

# Run any build steps (e.g. migrations, npm scripts, etc.)
run_build_steps() {
    if [ "${BUILD:-}" != "1" ]; then return; fi

    log INFO "Running build steps..."

    log INFO "Running npm install and build..."
    docker run --rm -v "$(pwd):/usr/src/app" -w /usr/src/app "node:${NODE_VERSION}-slim" /bin/bash -c "npm install && npm run build"
}

# Stop all docker containers
stop_containers() {
    if [ "${STOP:-}" == "1" ] && [ "${START:-}" == "0" ]
    then
        log INFO "Stopping and removing containers..."
        # shellcheck disable=SC2068
        docker compose ${COMPOSE_EXTRAS[@]:-} --profile $PROFILE down --timeout 120
    fi
}

# Restart all containers (asynchronously) regardless of new builds
restart_containers() {
    if [ "${STOP:-}" == "1" ] && [ "${START:-}" == "1" ]
    then
        log INFO "Restarting containers..."
        # shellcheck disable=SC2068
        docker compose ${COMPOSE_EXTRAS[@]:-} --profile $PROFILE restart --timeout 120
        log_containers
        remove_dangling
    fi
}

# Start the docker containers (restarting any re-built containers)
start_containers() {
    if [ "${STOP:-}" == "0" ] && [ "${START:-}" == "1" ]
    then
        log INFO "Starting containers..."
        # shellcheck disable=SC2068
        docker compose ${COMPOSE_EXTRAS[@]:-} --profile $PROFILE up \
            --detach --timeout 120
        log_containers
        remove_dangling
    fi
}

# Logs docker containers output to log files
log_containers() {
    log INFO "Establishing docker container logging..."
    # Logs dir created earlier, so no need to re-create here
    touch "$NGINX_LOG"
    docker logs --follow nginx &>> "$NGINX_LOG" &
    touch "$WEB_APP_LOG"
    docker logs --follow web_app &>> "$WEB_APP_LOG" &
    touch "$DB_LOG"
    docker logs --follow db &>> "$DB_LOG" &
    touch "$MIGRATION_LOG"
    docker logs --follow migration_app &>> "$MIGRATION_LOG" &

    if [ "${PROD:-}" == "1" ]
    then
        touch "$CERTBOT_LOG"
        docker logs --follow certbot &>> "$CERTBOT_LOG" &
    fi
}

# Removes all dangling images and builds
remove_dangling() {
    log INFO "Removing dangling images..."
    docker image prune --force
    log INFO "Removing dangling builds..."
    docker builder prune --force
}

# Main function--run all the steps
main() {
    log INFO "Running scripts/deploy.sh..."
    announce_vars
    update_branch
    install_crontab
    set_profile
    set_extras
    build_images
    run_build_steps
    stop_containers
    restart_containers
    start_containers
}


# ---------------------------------------------------------------------------
# SCRIPT START
# ---------------------------------------------------------------------------
source_environment
# -------------------- READ OPTIONS --------------------
# Opts
while test $# -gt 0
do
    case "$1" in
        --help) echo_usage; exit 0
            ;;
        --debug) DEBUG=1
            ;;
        --prod) PROD=1
            ;;
        --dev) PROD=0
            ;;
        --down) BUILD=0; START=0; STOP=1
            ;;
        --restart) START=1; STOP=1
            ;;
        --skip-build) BUILD=0
            ;;
        --from-scratch) FROM_SCRATCH=1
            ;;
        --if-needed) IF_NEEDED=1
            ;;
        *) echo "Unknown option: $1"; echo_usage; exit 1
            ;;
    esac
    shift
done
# -------------------- RUN MAIN --------------------
main
