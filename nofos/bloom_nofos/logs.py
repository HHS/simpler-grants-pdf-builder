import logging


class PrintLoggerNameFilter(logging.Filter):
    """
    Logging filter that prints the logger name and level of each log record
    to stdout for debugging purposes.

    Useful during development to identify which logger is emitting specific
    log entries, especially when tuning or suppressing noisy logs.
    """

    def filter(self, record):
        print(f"[DEBUG] logger: {record.name} | level: {record.levelname}")
        return True


class SuppressWellKnown404Filter(logging.Filter):
    """
    Logging filter that suppresses WARNING-level logs for requests to
    .well-known URLs (e.g., /.well-known/appspecific/...).

    These requests are often made by browser tools like Chrome DevTools and
    do not need to be logged, even when they result in 404s.
    """

    def filter(self, record):
        if record.levelno == logging.WARNING:
            msg = record.getMessage()
            return "/.well-known/" not in msg
        return True
