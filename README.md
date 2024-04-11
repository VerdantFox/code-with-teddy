# code-with-teddy

My portfolio, blog, and mini-projects website, revamped for 2024

## Setup

You'll need to install a few things to get the website running locally. The website is built with Python and FastAPI for the backend, and uses TailwindCSS, Alpine.js and HTMX on the front end. The database is Postgres with the SQLAlchemy ORM.

### Python

First, install [uv](https://github.com/astral-sh/uv) for package management. I recommend installing [pipx](https://github.com/pypa/pipx) and then:

```bash
pipx install uv
```

Then install python environment:

```bash
# Create a virtual environment
uv venv --python=3.11 venv
source venv/bin/activate

# Install DEV dependencies
uv pip install -r requirements-dev.txt
```

Update requirements with:

```bash
./scripts/update-requirements.sh
```

### Node

First, install the latest versions of npm and node. Then install the node environment:

```bash
# Install node environment
npm install
```

### Docker

You'll need to install Docker to run the website locally. Even if not running the app itself in Docker, its used for running the Postgres database. You can install Docker from [here](https://docs.docker.com/get-docker/).

## Running the app

### Start the database

To start up the local database for development, run:

```bash
python -m scripts.start_local_postgres
```

👆 By default this creates a Postgres docker container and populates it with dummy data.

### Start the app

To run the app locally, you can use the following command:

```bash
python -m scripts.run_dev
```

This will start an instance of `tailwind` that will build the CSS and watch for changes. It will also update the Python requirements, start up the Postgres database docker container if it is not already running, and start the FastAPI server.

## Testing

Tests are written in Python with pytest. They include functional tests against the FastAPI endpoints, unit tests against key functions, and end-to-end tests using Playwright.

To run the playwright tests, you'll need to first install the playwright browsers:

```bash
playwright install
```

To run tests use one of the following commands:

```bash
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

```bash
pre-commit install
```

To run the checks manually, use:

```bash
pre-commit run --all-files
```

Lint checks include (but are not limited to):

- ruff (lots of Python lint checks, auto-fixes, and autoformatting)
- mypy (static Python type checking)
- prettier (HTML, CSS, JS, YAML formatting)

## Updating dependencies

To update dependencies, run:

```bash
# Update Python dependencies
./scripts/update-requirements.sh

# Update Node dependencies
./scripts/update-requirements.sh --node

# Update static dependencies
./scripts/update-requirements.sh --static

# Update pre-commit hooks
./scripts/update-requirements.sh --pre-commit

# Update all dependencies
./scripts/update-requirements.sh --all
```

## CI/CD

TODO: Add CI/CD instructions
