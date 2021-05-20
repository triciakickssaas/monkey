import os
import sys

__author__ = "itay.mizeretz"


def get_default_data_dir() -> str:
    is_windows_os = sys.platform.startswith("win")
    if is_windows_os:
        return r"%AppData%\monkey_island"
    else:
        return r"$HOME/.monkey_island"


SERVER_CONFIG_FILENAME = "server_config.json"

MONKEY_ISLAND_ABS_PATH = os.path.join(os.getcwd(), "monkey_island")

DEFAULT_DATA_DIR = os.path.expandvars(get_default_data_dir())

DEFAULT_MONKEY_TTL_EXPIRY_DURATION_IN_SECONDS = 60 * 5

DEFAULT_SERVER_CONFIG_PATH = os.path.expandvars(
    os.path.join(DEFAULT_DATA_DIR, SERVER_CONFIG_FILENAME)
)

DEFAULT_DEVELOP_SERVER_CONFIG_PATH = os.path.join(
    MONKEY_ISLAND_ABS_PATH, "cc", f"{SERVER_CONFIG_FILENAME}.develop"
)
