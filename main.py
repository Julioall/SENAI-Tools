import sys
from pathlib import Path

from senai_tools.app import run_app
from senai_tools.tools import get_tools


def resource_path(relative_path: str) -> Path:
    """Resolve paths no matter if running via python ou binário PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(base_path) / relative_path


def main() -> None:
    icon_path = resource_path("logo.ico")
    run_app(get_tools(), icon_path=icon_path)


if __name__ == "__main__":
    main()
