def strip_null_and_blank_nofo_keys(nofo_dict, *, preserve_keys):
    """
    Remove top-level keys whose value is None or "".
    Leaves preserved keys (like "sections") completely untouched.
    """
    cleaned = {}
    for k, v in nofo_dict.items():
        if k in preserve_keys:
            cleaned[k] = v
            continue

        if v is None or v == "":
            continue

        cleaned[k] = v

    return cleaned
