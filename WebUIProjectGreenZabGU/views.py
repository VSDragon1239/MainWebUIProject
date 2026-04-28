import logging
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.http import Http404

from .forms import BlogPostForm, BlogPostImageFormSet
from WebUiProject.models import Project, Blog, EcoTransactionType, EcoTask, UserTaskCompletion, \
    EcoHabit, UserHabitLog, EcoHabitCategory
from .permissions import RoleRequiredMixin

from django.views import View

from .services import EcoCoinService

logger = logging.getLogger(__name__)


class IndexGreenView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/index.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Страница для участников
#   Список проектов в которых участвуете, информация, доступ к документам, их редактирование, и т.д.
class ParticipantView(RoleRequiredMixin, TemplateView):
    required_roles = ['Участники']
    template_name = "pages/participant.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Страница для руководителя проекта (-ов)
#   Список проектов     -   добавить (в систему), изменить (данные (кто участвует), ссылки, документы), удалить (вместе со всем),
#   Участников проекта  -   добавить (зарегистрировать в систему и добавить к проекту), изменить (в каком проекте участвует, в каком уже нет), удалить (из системы учетную запись)
class LeaderView(RoleRequiredMixin, TemplateView):
    required_roles = ['Руководители']
    template_name = "pages/leaders.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Страница для администратора сайта
#   Список руководителей    -   добавить (роль), изменить (роль), удалить (если нет других ролей - удаление учётной записи),
#   Контент-менеджеров      -   добавить (роль), изменить (роль), удалить (зависит от других ролей, если их нет - удаление учётной записи),
#   Участников в системе    -   добавить (создание учётной записи в систему), изменить (профиль), удалить (саму учётную запись)
#   Работа с проектами (создание, изменени, удаление) и назначение ролей
class AdminView(RoleRequiredMixin, TemplateView):
    required_roles = ['Администраторы']
    template_name = "pages/admin.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Проекты
        context["projects"] = Project.objects.all().select_related('type').prefetch_related('leaders', 'members')

        # Группы (для фильтрации)
        leaders_group = Group.objects.get(name='Руководители')
        managers_group = Group.objects.get(name='Контент менеджер')
        members_group = Group.objects.get(name='Участники')

        # Пользователи по категориям
        context["leaders"] = User.objects.filter(groups=leaders_group)
        context["managers"] = User.objects.filter(groups=managers_group)
        context["members"] = User.objects.filter(groups=members_group)

        # Все пользователи (для быстрого поиска)
        context["users"] = User.objects.all()

        return context


class ContentManagerView(RoleRequiredMixin, TemplateView):
    required_roles = ['Контент менеджер']
    template_name = "pages/content_manager.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class AddBlogPostView(RoleRequiredMixin, CreateView):
    required_roles = ['Контент менеджер']
    template_name = "pages/add_blog_post.html"
    model = Blog
    form_class = BlogPostForm
    success_url = reverse_lazy("blog")

    def get(self, request, *args, **kwargs):
        # form = self.form_class()
        # formset = BlogPostImageFormSet()
        # request["form"] = form
        # request["formset"] = formset
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = BlogPostImageFormSet(self.request.POST, self.request.FILES)
        else:
            context["formset"] = BlogPostImageFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class AchievementsView(TemplateView):
    template_name = "pages/achievements.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CategoriesEventsView(TemplateView):
    template_name = "pages/categories_events.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EventsView(TemplateView):
    template_name = "pages/events.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EventDetailsView(TemplateView):
    template_name = "pages/event_details.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoHabitsTrackerView(TemplateView):
    template_name = "pages/eco_habits_tracker.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoTasksTrackerView(TemplateView):
    template_name = "pages/eco_tasks_tracker.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed_ids = UserTaskCompletion.objects.filter(
            user=self.request.user
        ).values_list('task_id', flat=True)

        # 2. Выводим ТОЛЬКО те активные задания, которых НЕТ в списке выполненных
        tasks = EcoTask.objects.filter(is_active=True).exclude(pk__in=completed_ids)

        context['tasks'] = tasks
        context['completed_task_ids'] = set(completed_ids)
        return context


class EcoTaskDetailsView(LoginRequiredMixin,
                         DetailView):  # DetailView от Django — он сам найдет задачу в БД по ID из URL или выдаст красивую ошибку 404, если задача не существует.
    """Детальная страница конкретного задания"""
    model = EcoTask
    template_name = "pages/eco_task_details.html"
    context_object_name = 'task'  # В шаблоне объект будет доступен как {{ task }}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Проверяем, выполнил ли текущий пользователь ЭТУ задачу
        is_completed = UserTaskCompletion.objects.filter(
            user=self.request.user,
            task=self.object
        ).exists()

        context['is_completed'] = is_completed
        return context


class CompleteEcoTaskView(LoginRequiredMixin, View):
    """
    Эта вьюха срабатывает когда пользователь нажимает кнопку "Выполнить".
    """

    def post(self, request, task_id):
        task = get_object_or_404(EcoTask, pk=task_id, is_active=True)

        # 1. Проверка на уровне приложения (чтобы не гонять лишние SQL запросы к БД)
        if UserTaskCompletion.objects.filter(user=request.user, task=task).exists():
            return JsonResponse({"error": "Вы уже выполнили это задание"}, status=400)

        # 2. Формируем уникальный ключ для нашего сервиса
        external_id = f"task:{task.id}:user:{request.user.id}"

        try:
            # Оборачиваем в atomic: если коины не начислятся, факт выполнения тоже не запишется
            with db_transaction.atomic():

                # Вызываем наш сервис! Он заблокирует кошелек и обновит баланс
                new_balance = EcoCoinService.credit(
                    user=request.user,
                    amount=task.reward,
                    tx_type=EcoTransactionType.TASK_COMPLETED,
                    external_id=external_id
                )

                # Записываем факт выполнения ТОЛЬКО если транзакция с коинами прошла успешно
                UserTaskCompletion.objects.create(user=request.user, task=task)

            # Возвращаем успешный ответ и НОВЫЙ баланс для обновления на экране
            return JsonResponse({
                "status": "success",
                "message": f"+{task.reward} ECO получено!",
                "new_balance": str(new_balance)
            })

        except IntegrityError:
            # Срабатывает, если concurrent-запрос (две открытые вкладки) прошли проверку выше одновременно,
            # но база данных (через UniqueConstraint в сервисе или unique_together) отдала ошибку дубликата.
            return JsonResponse({"error": "Задание уже было выполнено (система)"}, status=400)

        except Exception as e:
            # Логируем непредвиденную ошибку (например, падение БД)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error completing task {task_id}: {str(e)}")
            return JsonResponse({"error": "Произошла ошибка на сервере"}, status=500)


class MarkHabitDoneView(LoginRequiredMixin, View):  # LoginRequiredMixin гарантирует,
    # что метод сработает только для авторизованных пользователей
    def post(self, request, habit_id):
        try:
            # external_id формируем так: habit:5:user:2 (чтобы за один день за одну привычку дать коины 1 раз)
            ext_id = f"habit:{habit_id}:user:{request.user.id}:date:{datetime.now().strftime('%Y-%m-%d')}"

            new_balance = EcoCoinService.credit(
                user=request.user,
                amount=5,
                tx_type=EcoTransactionType.HABIT_TRACKED,
                external_id=ext_id
            )
            return JsonResponse({"status": "success", "new_balance": str(new_balance)})

        except Exception as e:
            # Если попытка дублирования (UniqueConstraint) или другая ошибка
            return JsonResponse({"status": "error", "message": str(e)}, status=400)


class EcoHabitsCategoriesView(LoginRequiredMixin, ListView):
    """Страница выбора категории привычек"""
    model = EcoHabitCategory
    template_name = "pages/eco_habits_categories.html"
    context_object_name = 'categories'


class EcoHabitsView(LoginRequiredMixin, ListView):
    """Список привычек внутри конкретной категории"""
    model = EcoHabit
    template_name = "pages/eco_habits.html"
    context_object_name = 'habits'

    def get_queryset(self):
        # Получаем категории из URL (pk)
        category_id = self.kwargs.get('pk')
        return EcoHabit.objects.filter(is_active=True, category_id=category_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(EcoHabitCategory, pk=self.kwargs.get('pk'))

        # Получаем сегодняшние серии для всех привычек разом (оптимизация запросов)
        today = timezone.localdate()
        logs_today = UserHabitLog.objects.filter(
            user=self.request.user,
            date_completed=today,
            habit__in=context['habits']
        ).values_list('habit_id', flat=True)

        context['completed_today_ids'] = set(logs_today)
        return context


class EcoHabitDetailsView(LoginRequiredMixin, DetailView):
    """Детальная страница привычки с инфой о серии"""
    model = EcoHabit
    template_name = "pages/eco_habit_details.html"
    context_object_name = 'habit'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        # Берем pk2 из URL (категория нам здесь для загрузки объекта не нужна)
        pk = self.kwargs.get('pk2')
        queryset = queryset.filter(pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("Привычка не найдена")

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Отмечено ли сегодня?
        today = timezone.localdate()
        context['is_completed_today'] = UserHabitLog.objects.filter(
            user=user, habit=self.object, date_completed=today
        ).exists()

        # Текущая серия (берем самый свежий лог)
        last_log = UserHabitLog.objects.filter(user=user, habit=self.object).first()
        context['current_streak'] = last_log.streak_count if last_log else 0

        return context


class LogEcoHabitView(LoginRequiredMixin, View):
    """AJAX обработчик нажатия кнопки 'Отметить'"""

    def post(self, request, pk):
        habit = get_object_or_404(EcoHabit, pk=pk, is_active=True)

        try:
            result = EcoCoinService.log_habit_and_credit(request.user, habit)

            streak_text = f"Серия: {result['streak']} дн.!"
            if result['is_new_streak'] and result['streak'] % 7 == 0:
                streak_text += " 🔥 Неделя!"

            return JsonResponse({
                "status": "success",
                "message": f"+{result['reward']} ECO. {streak_text}",
                "new_balance": str(result['balance']),
                "new_streak": result['streak']
            })

        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Habit Log Error: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Ошибка сервера"}, status=500)
