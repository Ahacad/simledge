# tests/test_config.py
import os
from unittest.mock import patch


def test_data_dir_returns_xdg_path():
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/test-xdg"}):
        from importlib import reload

        import simledge.compat

        reload(simledge.compat)
        result = simledge.compat.data_dir()
        assert result == "/tmp/test-xdg/simledge"


def test_config_dir_returns_xdg_path():
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test-xdg-config"}):
        from importlib import reload

        import simledge.compat

        reload(simledge.compat)
        result = simledge.compat.config_dir()
        assert result == "/tmp/test-xdg-config/simledge"
