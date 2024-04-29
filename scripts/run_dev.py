"""Run the app in development mode."""

import time
from typing import Annotated

import typer
from pynput.keyboard import Controller, Key

keyboard = Controller()
cli_app = typer.Typer(add_completion=False)


@cli_app.command()
def main(
    *,
    browser_sync: Annotated[
        bool,
        typer.Option(
            ...,
            "--browser-sync/--no-browser-sync",
            "-b/-nb",
            help="Don't run browser-sync.",
        ),
    ] = False,
    start_postgres: Annotated[
        bool,
        typer.Option(
            ...,
            "--start-postgres/--no-start-postgres",
            "-p/-np",
            help="Don't start a local postgres server.",
        ),
    ] = True,
) -> None:
    """Run the app in development mode."""
    run_tailwind()
    if browser_sync:
        run_browser_sync()
    run_uvicorn(start_postgres=start_postgres)


def run_cmd(args: list[str], *, new_terminal: bool = True) -> None:
    """Run a command in the opened terminal."""
    if new_terminal:
        open_new_terminal()
    keyboard.type(" ".join(args))
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)


def open_new_terminal() -> None:
    """Open a vscode terminal in a new window."""
    keyboard.press(Key.ctrl)
    keyboard.press(Key.shift)
    keyboard.press("`")

    keyboard.release(Key.ctrl)
    keyboard.release(Key.shift)
    keyboard.release("`")

    time.sleep(0.5)


def run_tailwind() -> None:
    """Start a tailwind server with hot reloading."""
    args = ["rm", "-f", "./app/web/html/static/css/tailwind-styles.css"]
    run_cmd(args, new_terminal=False)

    args = ["npm", "run", "watch"]
    run_cmd(args)


def run_uvicorn(*, start_postgres: bool) -> None:
    """Start a uvicorn server with hot reloading."""
    open_new_terminal()
    run_setup(start_postgres=start_postgres)
    args = [
        "uvicorn",
        '"app.web.main:create_app"',
        "--factory",
        "--host=0.0.0.0",
        "--reload",
        '--reload-include="*.html"',
        '--reload-include="*.css"',
        '--reload-include="*.js"',
    ]
    run_cmd(args, new_terminal=False)


def run_setup(*, start_postgres: bool) -> None:
    """Run the setup script."""
    args = ["uv", "pip", "sync", "requirements-dev.txt"]
    run_cmd(args, new_terminal=False)

    if start_postgres:
        args = ["docker", "start", "postgres"]
        run_cmd(args, new_terminal=False)


def run_browser_sync() -> None:
    """Run browser-sync with hot reloading."""
    args = [
        "browser-sync",
        "http://localhost:8000",
        "app/web/html/static",
        "-w",
        "-f",
        ".",
    ]
    run_cmd(args)


if __name__ == "__main__":
    cli_app()
