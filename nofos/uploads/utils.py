def get_display_size(size_bytes):
    if size_bytes < 1024:
        return "{} B".format(size_bytes)
    elif size_bytes < 1024 * 1024:
        size_kb = size_bytes / 1024
        return "{:.1f} KB".format(size_kb)
    else:
        size_mb = size_bytes / (1024 * 1024)
        return "{:.1f} MB".format(size_mb)


def strip_s3_hostname_suffix(value):
    return value.split(".", 1)[0] if value else value
