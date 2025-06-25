import logging
import re
import time
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.template import loader
from django.utils.deprecation import MiddlewareMixin


class BadRequestMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if isinstance(response, HttpResponseBadRequest):
            context = {"error_message": response.content.decode("utf-8")}
            template = loader.get_template("400.html")
            return HttpResponseBadRequest(template.render(context, request))
        return response


class JSONRequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log HTTP requests with timing and filtering
    """

    # Define patterns for static assets to exclude
    STATIC_ASSET_PATTERNS = [
        r"\.css$",
        r"\.js$",
        r"\.png$",
        r"\.jpg$",
        r"\.jpeg$",
        r"\.gif$",
        r"\.svg$",
        r"\.ico$",
        r"\.woff$",
        r"\.woff2$",
        r"\.ttf$",
        r"\.eot$",
        r"\.map$",
        r"/static/",
        r"/media/",
        r"/\.well-known/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.asset_regex = re.compile(
            "|".join(self.STATIC_ASSET_PATTERNS), re.IGNORECASE
        )
        self.logger = logging.getLogger("django.request")
        super().__init__(get_response)

    def process_request(self, request):
        """Store the start time"""
        request._start_time = time.time()
        return None

    def process_exception(self, request, exception):
        start_time = getattr(request, "_start_time", time.time())
        response_time_ms = (time.time() - start_time) * 1000

        error_data = {
            "method": request.method,
            "url": request.get_full_path(),
            "status": 500,
            "response_time": f"{response_time_ms:.3f}ms",
            "exception_type": exception.__class__.__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
        }

        if hasattr(request, "user") and request.user.is_authenticated:
            error_data["user_id"] = str(request.user.id)

        # Mark that we've handled this exception
        request._exception_handled_by_json_middleware = True

        # Handle expected errors differently
        if isinstance(exception, ValidationError):
            error_data["status"] = 400
            self.logger.warning("Validation Error", extra=error_data)
            return HttpResponseBadRequest("Validation failed")

        elif isinstance(exception, PermissionDenied):
            error_data["status"] = 403
            self.logger.warning("Permission Denied", extra=error_data)
            return HttpResponseForbidden("Permission denied")

        # Default for all other exceptions
        self.logger.error("Unhandled Exception", extra=error_data)
        return None  # Let Django handle it normally (500)

    def process_response(self, request, response):
        """Log the request using structured logging"""

        # Skip logging for static assets
        if self.should_skip_logging(request):
            return response

        # Calculate response time
        start_time = getattr(request, "_start_time", time.time())
        response_time_ms = (time.time() - start_time) * 1000

        # Determine log level based on status code
        status_code = response.status_code

        # Log with structured data
        extra_data = {
            "method": request.method,
            "url": request.get_full_path(),
            "status": status_code,
            "response_time": f"{response_time_ms:.3f}ms",
        }

        # Add optional fields
        if hasattr(request, "user") and request.user.is_authenticated:
            extra_data["user_id"] = str(request.user.id)

        is_prod = getattr(settings, "is_prod", False)

        if is_prod:
            # User agent - useful for identifying bots, mobile users
            if request.META.get("HTTP_USER_AGENT"):
                extra_data["user_agent"] = request.META.get("HTTP_USER_AGENT")

            # Referrer - shows where users came from
            if request.META.get("HTTP_REFERER"):
                extra_data["referrer"] = request.META.get("HTTP_REFERER")

        # Log at appropriate level
        if status_code >= 500:
            # catch exceptions we have already processed
            if getattr(request, "_exception_handled_by_json_middleware", False):
                return response
            self.logger.error("HTTP Request", extra=extra_data)
        elif status_code >= 400:
            self.logger.warning("HTTP Request", extra=extra_data)
        else:
            self.logger.info("HTTP Request", extra=extra_data)

        return response

    def should_skip_logging(self, request):
        """Check if we should skip logging this request"""
        path = request.get_full_path()
        return bool(self.asset_regex.search(path))
