"""PyInstaller entry point for the desktop app. `--engine api|worker|migrate` runs a part of the local engine
(the app starts these as its own child processes) without opening a window."""

import sys


def run(argv: list[str]) -> None:
    if "--engine" in argv:
        from mediafactory.desktop_engine import child_main

        child_main(argv)
    else:
        from mediafactory import desktop

        desktop.main()


if __name__ == "__main__":
    run(sys.argv[1:])
