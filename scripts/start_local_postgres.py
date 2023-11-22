"""start_local_postgres: Starts a postgres container.

And populates the postgres database from the SQLAlchemy models.

Run with `python -m dev_tools.start_local_postgres --help`
"""
import contextlib
import logging
import os
import time
from typing import Optional
from urllib.parse import quote_plus

import docker
import typer
from docker import APIClient
from docker.errors import NotFound
from docker.models.containers import Container
from pydantic import BaseModel

from app.datastore import database, db_models
from scripts.alembic import upgrade

HEALTH_CHECK_TIMEOUT = 15

logger = logging.getLogger(__file__)


class DBVars(BaseModel):
    """Database variables."""

    container_name: str
    username: str
    password: str
    database: str
    port: int

    def get_connection_string(self) -> str:
        """Get the connection string for the postgres container."""
        return (
            f"postgresql+psycopg2://{quote_plus(self.username)}:{quote_plus(self.password)}"
            f"@localhost:{self.port}/{self.database}"
        )


def _set_env_vars(db_vars: DBVars) -> None:
    """Set environment variables for the postgres container."""
    os.environ["DB_CONNECTION_STRING_SECRET"] = db_vars.get_connection_string()


def _get_docker_client() -> docker.DockerClient:
    """Get the docker client."""
    return docker.from_env()


def _wait_for_container_health(container: Container, health: str = "healthy") -> None:
    """Wait for container health status check to pass."""
    interval = 0.1  # seconds
    for _ in range(int(HEALTH_CHECK_TIMEOUT / interval)):
        if _get_container_health(container) == health:
            # Seems that container is still not ready for a short period after health check passes
            time.sleep(1)
            return
        time.sleep(interval)


def _get_container_health(container: Container) -> str:
    """Get the health status of the newly created postgres container."""
    docker_api_client = APIClient()
    inspect_results = docker_api_client.inspect_container(container.name)
    status = str(inspect_results["State"]["Health"]["Status"])
    docker_api_client.close()
    return status


def teardown_container(*, db_vars: DBVars, docker_client: APIClient) -> None:
    """Teardown an existing postgres container of the same name."""
    with contextlib.suppress(NotFound):
        pg_container = docker_client.containers.get(db_vars.container_name)
        pg_container.remove(force=True)


def _create_postgres_container(
    *,
    db_vars: DBVars,
    docker_client: APIClient,
) -> Container:
    """Create the postgres container."""
    environment = {
        "POSTGRES_USER": db_vars.username,
        "POSTGRES_PASSWORD": db_vars.password,
        "POSTGRES_DB": db_vars.database,
    }
    return docker_client.containers.run(
        image="postgres:latest",
        detach=True,
        name=db_vars.container_name,
        ports={5432: db_vars.port},
        environment=environment,
        healthcheck={
            "test": [
                "CMD",
                "pg_isready",
                "-U",
                db_vars.username,
                "-d",
                db_vars.database,
            ],
            "interval": 100000000,
        },
    )


def _create_database() -> None:
    """Create a postgres database if it does not exist."""
    db_models.Base.metadata.create_all(bind=database.engine)


def _run_migrations(migration_version: str) -> None:
    """Run migrations to a specific version."""
    upgrade(revision=migration_version)


def _announce_vars(db_vars: DBVars) -> None:
    """Announce connection variables."""
    logger.info("[underline]Connection variables:[/underline]")
    logger.info("postgres container name: [yellow]%s[/yellow]", db_vars.container_name)
    logger.info("postgres port:           [cyan]%s[/cyan]", db_vars.port)
    logger.info("postgres username:       [yellow]%s[/yellow]", db_vars.username)
    logger.info("postgres password:       [yellow]%s[/yellow]", db_vars.password)
    logger.info("postgres database:       [yellow]%s[/yellow]", db_vars.database)
    logger.info(
        "connection string:       [green]%s[/green]",
        db_vars.get_connection_string(),
    )


def create_container_and_db(  # noqa: PLR0913 too-many-args
    db_vars: DBVars,
    *,
    teardown: bool = True,
    create_db: bool = True,
    migration_version: str | None = None,
    populate: bool = False,  # noqa: ARG001 unused-function-arg
    silent: bool = False,
) -> Container:
    """Start the postgres container and populate the database."""
    if not silent:
        logger.setLevel(logging.INFO)
    _set_env_vars(db_vars)
    docker_client = _get_docker_client()
    if teardown:
        logger.info("Tearing down existing container...")
        teardown_container(db_vars=db_vars, docker_client=docker_client)
    logger.info("Creating postgres container...")
    container = _create_postgres_container(db_vars=db_vars, docker_client=docker_client)
    logger.info("Waiting for container health check to pass...")
    _wait_for_container_health(container)
    if migration_version:
        logger.info("Running migrations to %s...", migration_version)
        _run_migrations(migration_version)
    elif create_db:
        logger.info("Creating database...")
        _create_database()
    # if populate:
    #     logger.info("Populating database...")  # noqa: ERA001
    #     populate_db.populate_database()  # noqa: ERA001
    _announce_vars(db_vars)
    return container


class Opts:
    """Options for the typer function script."""

    default = "postgres"
    container_name = typer.Option(default, help="Postgres container name.")
    username = typer.Option(default, help="Postgres username.")
    password = typer.Option(default, help="Postgres password.")
    database = typer.Option(default, help="Postgres database name.")
    port = typer.Option(5432, help="Postgres port.")
    teardown_help = "Teardown an existing postgres container of the same name before creating a new one."
    teardown = typer.Option(default=True, help=teardown_help)
    create_db_help = "Create the database tables as specified by the SQLAlchemy models in db_models."
    create_db = typer.Option(default=True, help=create_db_help)
    migration_help = (
        "Database migration version. If specified, the database "
        "will be migrated to this version. Overrides --create-db. "
        "Use 'head' to migrate to the latest version."
    )
    migration_version = typer.Option(None, "--migrate", help=migration_help)
    populate = typer.Option(default=True, help="Populate the database with dummy data.")
    silent = typer.Option(default=False, help="Suppress all output.")


cli_app = typer.Typer(add_completion=False)


@cli_app.command()
def typer_main(  # noqa: PLR0913 too-many-arguments
    *,
    container_name: str = Opts.container_name,
    username: str = Opts.username,
    password: str = Opts.password,
    database: str = Opts.database,
    port: int = Opts.port,
    teardown: bool = Opts.teardown,
    create_db: bool = Opts.create_db,
    migration_version: Optional[str] = Opts.migration_version,  # noqa: UP007
    populate: bool = Opts.populate,
    silent: bool = Opts.silent,
) -> None:
    """Create a postgres docker container and postgres database with tables."""
    db_vars = DBVars(
        container_name=container_name,
        username=username,
        password=password,
        database=database,
        port=port,
    )
    create_container_and_db(
        db_vars=db_vars,
        teardown=teardown,
        create_db=create_db,
        migration_version=migration_version,
        populate=populate,
        silent=silent,
    )


if __name__ == "__main__":
    cli_app()
