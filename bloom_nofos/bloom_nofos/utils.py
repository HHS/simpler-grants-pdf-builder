from django.utils.timezone import now, timedelta


def cast_to_boolean(value_str):
    """
    Cast a string value to a boolean.

    Args:
    value_str (str): The string to be cast to a boolean.

    Returns:
    bool: The boolean value of the string.

    Raises:
    ValueError: If the string cannot be cast to a boolean.
    """
    # Define truthy and falsy values
    truthy_values = [True, "true", "True", "TRUE", "1", "t"]
    falsy_values = [False, "false", "False", "FALSE", "0", "f", ""]

    if value_str in truthy_values:
        return True
    elif value_str in falsy_values:
        return False
    else:
        raise ValueError(f"Value '{value_str}' is not a valid boolean string")


def is_docraptor_live_mode_active(last_updated):
    # Check if the timestamp is more than 2 minutes old
    if last_updated and now() - last_updated < timedelta(minutes=2):
        return True

    return False
