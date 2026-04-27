"""
URL configuration for MainWebUIProject project.

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
from django.urls import path, include
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView

from django.conf import settings
from django.conf.urls.static import static

from WebUiProject.views import NoAccessView

urlpatterns = [
    path('sysadmin/', admin.site.urls),
    path('main/', include('WebUiProject.urls')),  # Доступ по адресу /main/
    path('main/green-zabgu/', include('WebUIProjectGreenZabGU.urls')),  # Доступ по адресу /green-zabgu/

    # Системные страницы
    # path('upload-file/', UploadFileView.as_view(), name='upload_file'),
    path('no-access/', NoAccessView.as_view(), name='no-access'),
    path(
        'login/',
        LoginView.as_view(
            template_name="webuiproject/pages/auth.html",
            redirect_authenticated_user=True,
            next_page="/profile/",
        ),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(
            next_page="/login/"
        ),
        name="logout",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
