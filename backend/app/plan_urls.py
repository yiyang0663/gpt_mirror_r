from django.urls import path

from app.accounts.views.plan import ServicePlanView, ServicePlanEnumView

urlpatterns = [
    path("", ServicePlanView.as_view()),
    path("enum", ServicePlanEnumView.as_view()),
]
