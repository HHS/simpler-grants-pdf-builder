import re


def match_view_url(url):
    """
    Check if the given URL matches the pattern "/nofos/{integer}".

    Args:
    url (str): The URL to be checked.

    Returns:
    bool: True if the URL matches the pattern, False otherwise.
    """
    # Regular expression to match the specified pattern
    pattern = r"^/nofos/\d+$"

    return bool(re.match(pattern, url))
