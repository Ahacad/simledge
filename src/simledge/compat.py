"""Platform detection and path helpers."""

import os
import sys

LINUX = sys.platform == "linux"
WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def data_dir():
    if WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "simledge")
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "simledge")


def config_dir():
    if WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "simledge")
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "simledge")
