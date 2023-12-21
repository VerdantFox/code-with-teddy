"""Run the app in development mode."""
import time
from typing import Annotated

import typer
from pynput.keyboard import Controller, Key

keyboard = Controller()
cli_app = typer.Typer(add_completion=False)


class Opts:
    """Options for the typer function script."""

    no_browser_sync_help = "Don't run browser-sync."
    no_browser_sync = typer.Option(..., help="Don't run browser-sync.")


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
    ] = True,
) -> None:
    """Run the app in development mode."""
    run_tailwind()
    if browser_sync:
        run_browser_sync()
    run_uvicorn()


def open_new_terminal() -> None:
    """Open a vscode terminal in a new window."""
    keyboard.press(Key.ctrl)
    keyboard.press(Key.shift)
    keyboard.press("`")

    keyboard.release(Key.ctrl)
    keyboard.release(Key.shift)
    keyboard.release("`")

    time.sleep(0.5)


def run_cmd(args: list[str]) -> None:
    """Run a command in the opened terminal."""
    open_new_terminal()
    keyboard.type(" ".join(args))
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)


def run_tailwind() -> None:
    """Start a tailwind server with hot reloading."""
    args = ["npm", "run", "watch"]
    run_cmd(args)


def run_uvicorn() -> None:
    """Start a uvicorn server with hot reloading."""
    args = [
        "uvicorn",
        "app.web.main:app",
        "--host=0.0.0.0",
        "--reload",
        '--reload-include="*.html"',
        '--reload-include="*.css"',
        '--reload-include="*.js"',
    ]
    run_cmd(args)


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
