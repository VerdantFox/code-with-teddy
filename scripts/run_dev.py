import time

from pynput.keyboard import Controller, Key

keyboard = Controller()


def main() -> None:
    run_tailwind()
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
        "--reload",
        '--reload-include="*.html"',
        '--reload-include="*.css"',
        '--reload-include="*.js"',
    ]
    run_cmd(args)


def run_browser_sync() -> None:
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
    main()
