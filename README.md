# code-with-teddy

My portfolio, blog, and mini-projects website, revamped for 2024

For a comprehensive technical description of the application architecture, technology stack, and design decisions, see [app_description.md](app_description.md).

## Setup

You'll need to install a few things to get the website running locally. The website is built with Python and FastAPI for the backend, and uses TailwindCSS, Alpine.js and HTMX on the front end. The database is Postgres with the SQLAlchemy ORM.

### Extra tools

- Install `tmux` for run-dev script
- Install `npx` for updating node dependencies.

### Python

First, install [uv](https://github.com/astral-sh/uv) for package management. I recommend installing it with the following command:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install python environment:

```shell
# Create a virtual environment
uv python install 3.14
uv venv --python=3.14 venv
source venv/bin/activate

# Install DEV dependencies
uv pip install -r requirements-dev.txt
```

Update requirements with:

```shell
./scripts/update-requirements.sh
```

### Node

First, install the latest versions of npm and node. Then install the node environment:

```shell
# Install node environment
npm install
```

### Docker

You'll need to install Docker to run the website locally. Even if not running the app itself in Docker, its used for running the Postgres database. [You can install Docker from here](https://docs.docker.com/get-docker/). Deployments use Docker and Docker Compose, so you'll need to install Docker Compose as well. [You can install Docker Compose from here](https://docs.docker.com/compose/install/).

Docker and Docker Compose configurations are in `docker_config`.

## Running the app

### Start the database locally

To start up the local database for development, run:

```shell
python -m scripts.start_local_postgres
```

👆 By default this creates a Postgres docker container and populates it with dummy data.

### Start the app locally

To run the app locally, you can use the following command:

```shell
./scripts/run-dev.sh
```

This will start an instance of `tailwind` that will build the CSS and watch for changes. It will also update the Python requirements, start up the Postgres database docker container if it is not already running, and start the FastAPI server.

### Run the app locally with Docker

To run the app in Docker, use the following command:

```shell
./scripts/deploy.sh
```

This command assumes that the Postgres database is not already started by `scripts/start_local_postgres.py`, and that the app is already running locally. You'll need to stop those processes before running the deploy script.

`./scripts/deploy.sh` deploys the dev environment by default which doesn't set up SSL for Caddy and doesn't write the crontab.

To stop the app, use:

```shell
./scripts/deploy.sh --down
```

For more options, use:

```shell
./scripts/deploy.sh --help
```

## Testing

Tests are written in Python with pytest. They include functional tests against the FastAPI endpoints, unit tests against key functions, and end-to-end tests using Playwright.

To run the playwright tests, you'll need to first install the playwright browsers:

```shell
playwright install
```

To run tests use one of the following commands:

```shell
# Standard run of functional and unit tests
pytest

# Run the playwright tests against localhost (requires a running instance of the app)
pytest --playwright local

# Run all tests (end-to-end against localhost), including the playwright tests
pytest --all

# To see test coverage:
pytest --cov --cov-report=term --cov-report=html
```

## Linting

I use pre-commit to run linting and formatting checks before every commit. Install the pre-commit hooks with:

```shell
pre-commit install
```

To run the checks manually, use:

```shell
pre-commit run --all-files
```

Lint checks include (but are not limited to):

- ruff (lots of Python lint checks, auto-fixes, and autoformatting)
- ty (static Python type checking)
- prettier (HTML, CSS, JS, YAML formatting)

## Updating dependencies

To update dependencies, run:

```shell
# Update Python dependencies
./scripts/update-requirements.sh --python

# Update Node dependencies
./scripts/update-requirements.sh --node

# Update static dependencies
./scripts/update-requirements.sh --static

# Update pre-commit hooks
./scripts/update-requirements.sh --pre-commit

# Update all dependencies
./scripts/update-requirements.sh --all
```

## Settings and secrets

Settings and secrets for the Python app are handled by the `app.settings` module, using the Pydantic `BaseSettings` class. Settings are loaded with this priority:

1. Docker secrets from `/run/secrets/<field_name>` (production)
2. `.env.local` (local developer overrides — not checked into version control)
3. `.env` (shared defaults — checked into version control)

Secrets are stored in the `secrets` directory (not checked into version control). Each secret is a file whose name is the secret key and whose content is the secret value.

## Database migrations

Database migrations are handled by Alembic. See the `README.md` in the `migrations` directory for more information.

## Deployment

### CI/CT/CD pipeline deployment

The CI/CT/CD pipeline is set up with GitHub Actions. The pipeline is defined in `.github/workflows/run-full-ci.yml`. [You can find the GitHub action pipeline here](https://github.com/VerdantFox/code-with-teddy/actions/workflows/run-full-ci.yml).

On every push to the main branch, the CI/CD pipeline will run the tests and linting. If all checks pass, the pipeline will update the `release-branch` branch to the latest commit on `main`. This branch is used for deployment to the production server.

Server-side, a cron job runs every 5 minutes to check for new commits on the `release-branch`. If a new commit is found, the server will pull the latest changes and restart the FastAPI server with `./scripts/deploy.sh --prod`.

### Manual deployment

To deploy the app manually, SSH into the server, go to the project, and use the following command:

```shell
./scripts/deploy.sh --prod
```

This will deploy the app in production mode, which includes setting up SSL for Caddy and write to the crontab to set up the server to restart the app daily and run further deployments by the CI/CD pipeline.

### SSL

SSL is handled automatically by Caddy via ACME (Let's Encrypt). No manual certificate management or Diffie-Hellman key generation is required. Caddy provisions and renews certificates automatically using the email configured in `caddy/Caddyfile`.
