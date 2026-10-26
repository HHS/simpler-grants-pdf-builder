from django.urls import path

from . import design_pilot_views as views

app_name = "design_pilot"
urlpatterns = [
    path("", views.index, name="index"),
    path("<uuid:candidate_id>/", views.review, name="review"),
    path("<uuid:candidate_id>/operation", views.operation, name="operation"),
    path("<uuid:candidate_id>/html", views.document, name="document"),
]
