from django.urls import path
from WebUiProject.views import IndexView, ContactsView, AboutView, ApplicationsView, \
    UserCreateView, UserUpdateView, UserDeleteView, EditProfileView

urlpatterns = [
    # Роли пользователей:
    path('', IndexView.as_view(), name='main'),

    # Управление пользователями:
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    # Для пользователей:

    path('profile/edit/', EditProfileView.as_view(), name='profile_edit'),  # Управление профилем

    # ы
    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('about/', AboutView.as_view(), name='about'),
    path('application/', ApplicationsView.as_view(), name='application'),
]
