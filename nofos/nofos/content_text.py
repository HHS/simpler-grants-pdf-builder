"""Shared text normalization with no application dependencies."""

import re


def clean_string(string):
    """Cleans the given string by removing extra whitespace."""
    return re.sub(r"\s+", " ", string.strip())
