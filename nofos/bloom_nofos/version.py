import os

import tomli
from django.conf import settings


def get_version():
    try:
        base_dir = settings.BASE_DIR
        pyproject_path = os.path.join(base_dir, "..", "pyproject.toml")

        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)
            return pyproject["tool"]["poetry"]["version"]
    except Exception:
        return "unknown"
