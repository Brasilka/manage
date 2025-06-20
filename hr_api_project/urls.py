"""
URL configuration for hr_api_project project.

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
from ninja import NinjaAPI
from core.api import api as core_api
from core.auth import router as auth_router

api = NinjaAPI(title="HR Management API")

api.add_router("/auth/", auth_router)     # авторизация
api.add_router("/core/", core_api)        # основное API

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),               # подключаем всё API здесь
]


