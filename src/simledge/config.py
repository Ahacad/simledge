"""Shared constants and paths for SimpLedge."""

import os

from simledge.compat import config_dir, data_dir

# Paths
DATA_DIR = data_dir()
CONFIG_DIR = config_dir()
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "simledge.db")
LOG_DIR = DATA_DIR
LOG_PATH = os.path.join(DATA_DIR, "simledge.log")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")
