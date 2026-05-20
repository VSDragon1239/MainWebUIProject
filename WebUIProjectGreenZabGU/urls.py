from django.urls import path
from WebUIProjectGreenZabGU.views import AddBlogPostView, AchievementsView, \
    CategoriesEventsView, EventsView, EcoHabitsTrackerView, EcoHabitsCategoriesView, \
    EcoHabitsView, EventDetailsView, EcoTasksTrackerView, EcoTaskDetailsView, EcoHabitDetailsView, \
    CompleteEcoTaskView, LogEcoHabitView, AdminView, ParticipantView, ContentManagerView, IndexGreenView, \
    BlogView, ProfileView, EcoTasksView, EcoBonusListView, EditEcoBonusView, AddEcoBonusView, RatingBoardView, \
    ContactsView

urlpatterns = [
    path('', IndexGreenView.as_view(), name='green_main'),  # Главная страница, надо чтобы было два вида - для не зарегистрированных и для участников
    path('administrations/', AdminView.as_view(), name='administrations'),      # Страница для администратора, позволяет управлять данными
    path('participant/', ParticipantView.as_view(), name='participant'),    # Страница для менеджеров, позволяет управлять и добавлять участников
    path('content_manager/', ContentManagerView.as_view(), name='content_manager'),  # Управляющий событиями, позволяет управлять новостями и блогами...

    # ============================ Информирование ============================
    path('news/', BlogView.as_view(), name='blog'),                             # Лента событий, мероприятий и т.п
    path('add_news_post/', AddBlogPostView.as_view(), name='add_news_post'),    # Функционал добавление новых новостей

    # ============================ Для пользователей ============================
    path('profile/', ProfileView.as_view(), name='profile'),  # Профиль пользователя
    path('achievements/', AchievementsView.as_view(), name='achievements'),                     # Список достижений
    path('categories-events/', CategoriesEventsView.as_view(), name='categories_events'),       # Категории событий
    path('eco-habits-tracker/', EcoHabitsTrackerView.as_view(), name='eco_habits_tracker'),     # Трекер зеленых привычек
    path('eco-tasks-tracker/', EcoTasksTrackerView.as_view(), name='eco_tasks_tracker'),        # Трекер зеленых заданий
    path('eco-tasks/', EcoTasksView.as_view(), name='eco_tasks'),                               # Список зеленых заданий
    path('rating-board/', RatingBoardView.as_view(), name='rating_board'),                      # Рейтинги
    path('contacts/', ContactsView.as_view(), name='contacts'),                                 # Контакты

    # ============================ Список категорий событий / мероприятий ============================
    path('categories-events/<int:pk>/events/', EventsView.as_view(), name='events'),                                        # Список событий / мероприятий
    path('categories-events/<int:pk1>/events/<int:pk2>/event-details/', EventDetailsView.as_view(), name='event_details'),  # Список событий / мероприятий
    path('eco-task-details/<int:pk>/', EcoTaskDetailsView.as_view(), name='eco_task_details'),                              # Детали зелённого задание

    # ============================ Для пользователей / Для инвесторов ============================
    path('eco-bonus-list/', EcoBonusListView.as_view(), name='eco_bonus_list'),
    path('edit-eco-bonus/<int:pk>/', EditEcoBonusView.as_view(), name='edit_eco_bonus'),
    path('add-eco-bonus/', AddEcoBonusView.as_view(), name='add_eco_bonus'),

    # ============================ Основные экологические страницы ============================
    path('eco-habits-categories/', EcoHabitsCategoriesView.as_view(), name='eco_habits_categories'),                        # Сортировка, экономия и другое... (Объединить в один с фильтром)
    path('categories/<int:pk>/eco-habits/', EcoHabitsView.as_view(), name='eco_habits'),                                    # Сортировка бу вещей / мусора
    path('categories/<int:pk1>/eco-habits/<int:pk2>/details', EcoHabitDetailsView.as_view(), name='eco_habit_details'),     # Детали экологических привычек

    # ============================ Основные системные страницы ============================
    path('eco-habits/log/<int:pk>/', LogEcoHabitView.as_view(), name='eco_habit_log'),
    path('eco-tasks/complete/<int:task_id>/', CompleteEcoTaskView.as_view(), name='eco_task_complete'),     # URL для AJAX запроса при нажатии на кнопку

]
