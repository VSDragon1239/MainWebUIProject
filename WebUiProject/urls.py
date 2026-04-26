from django.urls import path
from django.contrib import admin
from WebUiProject.views import IndexView, ContactsView, AboutView, ApplicationsView, BlogView, \
    ProfileView, UserCreateView, UserUpdateView, UserDeleteView, EditProfileView

urlpatterns = [
    # Роли пользователей:
    path('', IndexView.as_view(), name='main'),
    path('sysadmin/', admin.site.urls),

    # Управление пользователями:
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    # Для пользователей:
    path('profile/', ProfileView.as_view(), name='profile'),  # Профиль пользователя
    path('profile/edit/', EditProfileView.as_view(), name='profile_edit'),  # Управление профилем

    # Главная, основные страницы

    # Информирование
    path('news/', BlogView.as_view(), name='blog'),  # Лента событий, мероприятий и т.п

    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('about/', AboutView.as_view(), name='about'),
    path('application/', ApplicationsView.as_view(), name='application'),

]
