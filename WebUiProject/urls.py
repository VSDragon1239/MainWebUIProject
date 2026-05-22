from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from WebUiProject.views import IndexView, AboutView, ApplicationsView, \
    UserCreateView, UserUpdateView, UserDeleteView

urlpatterns = [
    # Роли пользователей:
    path('', IndexView.as_view(), name='main'),
    path('admin/', RedirectView.as_view(url='sysadmin/', permanent=True)),

    # Управление пользователями:
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    # Стандартные вьюхи Джанго для сброса пароля
    path('reset-password/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # О нас и наших спонсорах
    path('about/', AboutView.as_view(), name='about'),
    path('application/', ApplicationsView.as_view(), name='application'),
]
