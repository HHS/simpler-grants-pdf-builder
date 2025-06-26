import logging
import traceback

from pythonjsonlogger import jsonlogger

logger = logging.getLogger("django.request")


def log_exception(request, e, level="error", context=None, status=None):
    """
    Logs a structured JSON error using the same format as the middleware.

    Args:
        request: Django request object
        e: Exception instance
        level: "error" or "warning"
        context: Optional string to describe what failed
        status: Optional HTTP status code (e.g. 400)
    """
    log_data = {
        "exception_type": e.__class__.__name__,
        "exception_message": str(e),
        "traceback": traceback.format_exc(),
        "method": request.method,
        "url": request.get_full_path(),
    }

    if status:
        log_data["status"] = status
    if context:
        log_data["context"] = context
    if hasattr(request, "user") and request.user.is_authenticated:
        log_data["user_id"] = str(request.user.id)

    log_func = logger.warning if level == "warning" else logger.error
    log_func(context or "Unhandled exception", extra=log_data)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Always include these base fields
        if "levelname" not in log_record:
            log_record["levelname"] = record.levelname
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


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
