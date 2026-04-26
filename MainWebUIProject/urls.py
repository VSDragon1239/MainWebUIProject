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
from WebUiProject.views import IndexView, ContactsView, AboutView, ApplicationsView, BlogView, OtherView, \
    ProfileView, ParticipantView, AdminView, ContentManagerView, NoAccessView, UploadFileView, \
    AddBlogPostView, UserCreateView, UserUpdateView, UserDeleteView, AchievementsView, CategoriesEventsView, \
    EventsView, EcoHabitsTrackerView, EcoHabitsCategoriesView, EcoHabitsView, EventDetailsView, \
    EcoTasksTrackerView, EcoTaskDetailsView, EcoHabitDetailsView, CompleteEcoTaskView, EditProfileView, LogEcoHabitView

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Роли пользователей:
    path('sysadmin/', admin.site.urls),
    path('admin/', AdminView.as_view(), name='admin'),
    path('participant/', ParticipantView.as_view(), name='participant'),
    path('content_manager/', ContentManagerView.as_view(), name='content_manager'),             # Управляющий событиями
    # path('leader/', LeaderView.as_view(), name='leader'),
    # Управление пользователями:
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    # Для пользователей:
    path('profile/', ProfileView.as_view(), name='profile'),                                                          # Профиль пользователя
    path('profile/edit/', EditProfileView.as_view(), name='profile_edit'),                                               # Управление профилем
    path('achievements/', AchievementsView.as_view(), name='achievements'),                                              # Список достижений
    path('categories-events/', CategoriesEventsView.as_view(), name='categories_events'),                                  # Список категорий событий / мероприятий
    path('categories-events/<int:pk>/events/', EventsView.as_view(), name='events'),                                        # Список событий / мероприятий
    path('categories-events/<int:pk1>/events/<int:pk2>/event-details/', EventDetailsView.as_view(), name='event_details'),    # Список событий / мероприятий
    path('eco-habits-tracker/', EcoHabitsTrackerView.as_view(), name='eco_habits_tracker'),                                 # Трекер зеленых привычек
    path('eco-habits/log/<int:pk>/', LogEcoHabitView.as_view(), name='eco_habit_log'),
    path('eco-tasks-tracker/', EcoTasksTrackerView.as_view(), name='eco_tasks_tracker'),                                 # Трекер зеленых заданий
    path('eco-task-details/<int:pk>/', EcoTaskDetailsView.as_view(), name='eco_task_details'),                          # Детали зелённого задание
    # URL для AJAX запроса при нажатии на кнопку
    path('eco-tasks/complete/<int:task_id>/', CompleteEcoTaskView.as_view(), name='eco_task_complete'),

    # Главная, основные страницы
    path('', IndexView.as_view(), name='main'),
    path('eco-habits-categories/', EcoHabitsCategoriesView.as_view(), name='eco_habits_categories'),    # Зеленый вуз
    path('categories/<int:pk>/eco-habits/', EcoHabitsView.as_view(), name='eco_habits'),    # Сортировка бу вещей / мусора
    path('categories/<int:pk1>/eco-habits/<int:pk2>/details', EcoHabitDetailsView.as_view(), name='eco_habit_details'),    # Детали экологических привычек

    # Информирование
    path('news/', BlogView.as_view(), name='blog'),     # Лента событий, мероприятий и т.п
    path('add_news_post/', AddBlogPostView.as_view(), name='add_news_post'),

    # Системные страницы
    path('upload-file/', UploadFileView.as_view(), name='upload_file'),
    path('no-access/', NoAccessView.as_view(), name='no-access'),

    # path('projects/', ProjectsView.as_view(), name='projects'),
    # path('projects/create/', ProjectCreateView.as_view(), name='project_create'),
    # path('projects/create/type/', ProjectTypeCreateView.as_view(), name='project_type_create'),
    # path('projects/<int:pk>/edit/', ProjectUpdateView.as_view(), name='project_edit'),
    # path('projects/<int:pk>/delete/', ProjectsDeleteView.as_view(), name='project_delete'),
    # path('app/blender/', BlenderWorkspaceView.as_view(), name='blender_workspace'),
    # path('start-blender/', BlenderStartView.as_view(), name='start_blender'),
    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('about/', AboutView.as_view(), name='about'),
    path('application/', ApplicationsView.as_view(), name='application'),
    path('other/', OtherView.as_view(), name='other'),
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
    # path(
    #     "projects/<int:pk>/",
    #     ProjectDetailsView.as_view(),
    #     name="project"
    # ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
