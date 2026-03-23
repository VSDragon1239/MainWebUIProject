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
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from WebUiProject.views import IndexView, ProjectsView, ContactsView, AboutView, ApplicationsView, BlogView, OtherView, \
    ProfileView, ParticipantView, LeaderView, AdminView, AuthView, ProjectDetailsView, ContentManagerView, NoAccessView, \
    AddBlogPostView, UserCreateView, UserUpdateView, UserDeleteView, ProjectUpdateView, ProjectCreateView, \
    ProjectsDeleteView, ProjectTypeCreateView, upload_file

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', IndexView.as_view(), name='main'),
    path('upload-file/', upload_file, name='upload_file'),
    path('sysadmin/', admin.site.urls),
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    path('projects/', ProjectsView.as_view(), name='projects'),
    path('projects/create/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/create/type/', ProjectTypeCreateView.as_view(), name='project_type_create'),
    path('projects/<int:pk>/edit/', ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:pk>/delete/', ProjectsDeleteView.as_view(), name='project_delete'),
    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('about/', AboutView.as_view(), name='about'),
    path('application/', ApplicationsView.as_view(), name='application'),
    path('blog/', BlogView.as_view(), name='blog'),
    path('other/', OtherView.as_view(), name='other'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('participant/', ParticipantView.as_view(), name='participant'),
    path('leader/', LeaderView.as_view(), name='leader'),
    path('admin/', AdminView.as_view(), name='admin'),
    path('content_manager/', ContentManagerView.as_view(), name='content_manager'),
    path('add_blog_post/', AddBlogPostView.as_view(), name='add_blog_post'),
    path('no-access/', NoAccessView.as_view(), name='no-access'),
    path(
        'login/',
        LoginView.as_view(
            template_name="pages/auth.html",
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
    path(
        "projects/<int:pk>/",
        ProjectDetailsView.as_view(),
        name="project"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
