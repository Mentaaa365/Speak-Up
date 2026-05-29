"""
URL configuration for speakup_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("authentication/", include("apps.authentication.urls")),
    path("diagnosis/", include("apps.diagnosis.urls")),
    path("learning/", include("apps.learning.urls")),
    path("exams/", include("apps.exams.urls")),
    path("progress/", include("apps.progress.urls")),
    path("question_bank/", include("apps.question_bank.urls")),

    path("", RedirectView.as_view(url='/authentication/login/', permanent=False)),
]
