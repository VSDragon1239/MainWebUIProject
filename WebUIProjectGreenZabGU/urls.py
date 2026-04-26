from django.urls import path
from django.contrib import admin
from WebUIProjectGreenZabGU.views import AddBlogPostView, AchievementsView, \
    CategoriesEventsView, EventsView, EcoHabitsTrackerView, EcoHabitsCategoriesView, \
    EcoHabitsView, EventDetailsView, EcoTasksTrackerView, EcoTaskDetailsView, EcoHabitDetailsView, \
    CompleteEcoTaskView, LogEcoHabitView, AdminView, ParticipantView, ContentManagerView

urlpatterns = [
    # Роли пользователей:
    path('sysadmin/', admin.site.urls),
    path('admin/', AdminView.as_view(), name='admin'),
    path('participant/', ParticipantView.as_view(), name='participant'),
    path('content_manager/', ContentManagerView.as_view(), name='content_manager'),  # Управляющий событиями

    # ============================ Для пользователей ============================
    path('achievements/', AchievementsView.as_view(), name='achievements'),  # Список достижений
    path('categories-events/', CategoriesEventsView.as_view(), name='categories_events'),

    # ============================ Список категорий событий / мероприятий ============================
    path('categories-events/<int:pk>/events/', EventsView.as_view(), name='events'),  # Список событий / мероприятий
    path('categories-events/<int:pk1>/events/<int:pk2>/event-details/', EventDetailsView.as_view(), name='event_details'),  # Список событий / мероприятий
    path('eco-habits-tracker/', EcoHabitsTrackerView.as_view(), name='eco_habits_tracker'),  # Трекер зеленых привычек
    path('eco-habits/log/<int:pk>/', LogEcoHabitView.as_view(), name='eco_habit_log'),
    path('eco-tasks-tracker/', EcoTasksTrackerView.as_view(), name='eco_tasks_tracker'),  # Трекер зеленых заданий
    path('eco-task-details/<int:pk>/', EcoTaskDetailsView.as_view(), name='eco_task_details'),  # Детали зелённого задание
    # URL для AJAX запроса при нажатии на кнопку
    path('eco-tasks/complete/<int:task_id>/', CompleteEcoTaskView.as_view(), name='eco_task_complete'),

    # ============================ Главная, основные страницы ============================
    path('eco-habits-categories/', EcoHabitsCategoriesView.as_view(), name='eco_habits_categories'),  # Зеленый вуз
    path('categories/<int:pk>/eco-habits/', EcoHabitsView.as_view(), name='eco_habits'),  # Сортировка бу вещей / мусора
    path('categories/<int:pk1>/eco-habits/<int:pk2>/details', EcoHabitDetailsView.as_view(), name='eco_habit_details'),     # Детали экологических привычек

    # ============================ Информирование ============================
    path('add_news_post/', AddBlogPostView.as_view(), name='add_news_post'),
]
