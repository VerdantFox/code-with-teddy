"""start_local_postgres: Starts a postgres container.

And populates the postgres database from the SQLAlchemy models.

Run with `python -m dev_tools.start_local_postgres --help`
"""
import contextlib
import os
import time
from typing import Annotated, Any, Optional
from urllib.parse import quote_plus

import docker
import typer
from docker import APIClient
from docker import errors as docker_errors
from docker.models import containers as docker_containers
from rich.console import Console

from app.datastore import database, db_models
from scripts import populate_db
from scripts.alembic import upgrade

HEALTH_CHECK_TIMEOUT = 15

console = Console()


class DBBuilder:
    """Builds a postgres container and database."""

    def __init__(  # noqa: PLR0913 too-many-arguments
        self,
        *,
        container_name: str,
        username: str,
        password: str,
        database: str,
        port: int,
        teardown: bool,
        create_db: bool,
        migration_version: str | None,
        populate: bool,
        silent: bool,
    ) -> None:
        """Initialize the DBBuilder."""
        self.container_name: str = container_name
        self.username: str = username
        self.password: str = password
        self.database: str = database
        self.port: int = port
        self.teardown: bool = teardown
        self.create_db: bool = create_db
        self.migration_version: str | None = migration_version
        self.populate: bool = populate
        self.silent: bool = silent
        self.docker_client: docker.DockerClient = self.set_docker_client()
        self.container: docker_containers.Container | None = None

    def main(self) -> docker_containers.Container:
        """Start the postgres container and populate the database."""
        self.set_docker_client()
        if self.teardown:
            self.print("Tearing down existing container...")
            self.teardown_container()
        self.print("Creating postgres container...")
        self.create_postgres_container()
        self.print("Waiting for container health check to pass...")
        self.wait_for_container_health()
        if self.migration_version:
            self.print(f"Running migrations to {self.migration_version}...")
            self.run_migrations()
        elif self.create_db:
            self.print("Creating database...")
            self.create_database()
        if self.populate:
            self.print("Populating database...")
            populate_db.populate_database()
        self.announce_vars()
        return self.container

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print optionally."""
        if self.silent:
            return
        console.print(*args, **kwargs)

    def get_connection_string(self) -> str:
        """Get the connection string for the postgres container."""
        return (
            f"postgresql+psycopg2://{quote_plus(self.username)}:{quote_plus(self.password)}"
            f"@localhost:{self.port}/{self.database}"
        )

    def set_docker_client(self) -> docker.DockerClient:
        """Get the docker client."""
        os.environ["DB_CONNECTION_STRING"] = self.get_connection_string()
        return docker.from_env()

    def wait_for_container_health(self) -> None:
        """Wait for container health status check to pass."""
        interval = 0.1  # seconds
        for _ in range(int(HEALTH_CHECK_TIMEOUT / interval)):
            if self.get_container_health() == "healthy":
                # Seems that container is still not ready for a short period
                # after the health check passes.
                time.sleep(1)
                return
            time.sleep(interval)

    def get_container_health(self) -> str:
        """Get the health status of the newly created postgres container."""
        docker_api_client = APIClient()
        assert self.container
        inspect_results = docker_api_client.inspect_container(self.container.name)
        status = str(inspect_results["State"]["Health"]["Status"])
        docker_api_client.close()
        return status

    def teardown_container(self) -> None:
        """Teardown an existing postgres container of the same name."""
        with contextlib.suppress(docker_errors.NotFound):
            pg_container = self.docker_client.containers.get(self.container_name)
            pg_container.remove(force=True)

    def create_postgres_container(self) -> None:
        """Create the postgres container."""
        environment = {
            "POSTGRES_USER": self.username,
            "POSTGRES_PASSWORD": self.password,
            "POSTGRES_DB": self.database,
        }
        self.container = self.docker_client.containers.run(
            image="postgres:latest",
            detach=True,
            name=self.container_name,
            ports={5432: self.port},
            environment=environment,
            healthcheck={
                "test": [
                    "CMD",
                    "pg_isready",
                    "-U",
                    self.username,
                    "-d",
                    self.database,
                ],
                "interval": 100000000,
            },
        )

    @staticmethod
    def create_database() -> None:
        """Create a postgres database if it does not exist."""
        db_models.Base.metadata.create_all(bind=database.engine)

    def run_migrations(self) -> None:
        """Run migrations to a specific version."""
        assert self.migration_version
        upgrade(revision=self.migration_version)

    def announce_vars(self) -> None:
        """Announce connection variables."""
        self.print("[underline]Connection variables:[/underline]")
        self.print(f"postgres container name: [yellow]{self.container_name}[/yellow]")
        self.print(f"postgres port:           [cyan]{self.port}[/cyan]")
        self.print(f"postgres username:       [yellow]{self.username}[/yellow]")
        self.print(f"postgres password:       [yellow]{self.password}[/yellow]")
        self.print(f"postgres database:       [yellow]{self.database}[/yellow]")
        self.print(
            f"connection string:       [green]{self.get_connection_string()}[/green]",
        )


POSTGRES = "postgres"
TEARDOWN_HELP = (
    "Teardown an existing postgres container of the same name before creating a new one."
)
CREATE_DB_HELP = "Create the database tables as specified by the SQLAlchemy models in db_models."
MIGRATION_HELP = (
    "Database migration version. If specified, the database will be migrated to this version."
    " Overrides --create-db. Use 'head' to migrate to the latest version."
)


cli_app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


@cli_app.command()
def typer_main(  # noqa: PLR0913 too-many-arguments
    *,
    container_name: Annotated[str, typer.Option(help="Postgres container name.")] = POSTGRES,
    username: Annotated[str, typer.Option(help="Postgres username.")] = POSTGRES,
    password: Annotated[str, typer.Option(help="Postgres password.")] = POSTGRES,
    database: Annotated[str, typer.Option(help="Postgres database name.")] = POSTGRES,
    port: Annotated[int, typer.Option(help="Postgres port.")] = 5432,
    teardown: Annotated[bool, typer.Option(help=TEARDOWN_HELP)] = True,
    create_db: Annotated[bool, typer.Option(help=CREATE_DB_HELP)] = True,
    migration_version: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--migrate", help=MIGRATION_HELP),
    ] = None,
    populate: Annotated[bool, typer.Option(help="Populate the database with dummy data.")] = True,
    silent: Annotated[bool, typer.Option(help="Suppress all output.")] = False,
) -> None:
    """Create a postgres docker container and postgres database with tables."""
    db_builder = DBBuilder(
        container_name=container_name,
        username=username,
        password=password,
        database=database,
        port=port,
        teardown=teardown,
        create_db=create_db,
        migration_version=migration_version,
        populate=populate,
        silent=silent,
    )
    db_builder.main()


if __name__ == "__main__":
    cli_app()
