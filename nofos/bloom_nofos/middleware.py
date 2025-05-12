from django.http import HttpResponseBadRequest
from django.template import loader
from django.utils.deprecation import MiddlewareMixin


class BadRequestMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if isinstance(response, HttpResponseBadRequest):
            context = {"error_message": response.content.decode("utf-8")}
            template = loader.get_template("400.html")
            return HttpResponseBadRequest(template.render(context, request))
        return response
