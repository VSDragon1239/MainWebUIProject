import logging
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import Http404

from MainWebUIProject import settings
from .email_sender import send_templated_mail
from .forms import BlogPostForm, BlogPostImageFormSet, RegistrationRequestForm
from WebUiProject.models import Project, Blog, EcoTransactionType, EcoTask, UserTaskCompletion, \
    EcoHabit, UserHabitLog, EcoHabitCategory, Profile, RegistrationRequest
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


# Страница профиля (доступна всем (Участнику, Руководителю, Контент-менеджеру, Администратору))
class ProfileView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    required_roles = ["Участники", "Руководители", "Администраторы", "Контент менеджер"]
    login_url = "/login/"  # куда перенаправлять
    redirect_field_name = "next"  # параметр с origin
    template_name = "webuiprojectgreenzabgu/pages/profile.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user

        # БЕЗОПАСНОЕ получение профиля
        profile, _ = Profile.objects.get_or_create(user=user)
        context['profile'] = profile

        # Баланс
        context['eco_balance'] = EcoCoinService.get_balance(user)

        # Выполненные задания
        context['completed_tasks'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('-completed_at')

        # Приоритеты ролей (если у пользователя несколько групп)
        roles_priority = {
            'Администраторы': ('Администратор', 'danger'),
            'Контент менеджер': ('Контент-менеджер', 'info'),
            'Руководители': ('Руководитель', 'warning'),
            'Участники': ('Участник', 'secondary'),
        }

        user_groups = user.groups.values_list('name', flat=True)
        context['display_role'] = ('Без роли', 'light')  # Значение по умолчанию

        for group_name in user_groups:
            if group_name in roles_priority:
                context['display_role'] = roles_priority[group_name]
                break

        return context


# Страница для администратора сайта
class AdminView(RoleRequiredMixin, TemplateView):
    required_roles = ['Администраторы']
    template_name = "webuiprojectgreenzabgu/moderations/registration_requests.html"

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


class ContentManagerView(RoleRequiredMixin, TemplateView):
    required_roles = ['Контент менеджер']
    template_name = "pages/content_manager.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Страница с блогом и новостями
class BlogView(ListView):
    template_name = "pages/blog.html"
    model = Blog

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blogs_list = Blog.objects.all()
        context["blogs_list"] = blogs_list
        return context

    def get_queryset(self):
        return super().get_queryset().prefetch_related("images")


# Контактная информация
class ContactsView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/contacts.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_register'] = self.request.GET.get('action') == 'register'
        context['is_send'] = self.request.GET.get('action') == 'send'
        if 'form' not in context:
            context['form'] = RegistrationRequestForm()
        return context

    def post(self, request, *args, **kwargs):
        """Метод обрабатывает отправку формы (POST-запрос)"""
        form = RegistrationRequestForm(request.POST)

        if form.is_valid():
            # Извлекаем очищенные данные, если они верны
            fio = form.cleaned_data['fio']
            group = form.cleaned_data['group']
            phone = form.cleaned_data['phone']
            email = form.cleaned_data['email']

            # ТУТ код сохранения (например, создание записи в БД или отправка письма)
            RegistrationRequest.objects.create(
                fio=fio,
                group=group,
                phone=phone,
                email=email
            )

            send_templated_mail(
                subject="Ваша заявка в Green ZabGu получена",
                template_path="webuiprojectgreenzabgu/emails/registration_received.html",
                context_dict={"fio": fio, "group": group, "email": email},
                to_email=email
            )

            # Выводим сообщение об успехе и делаем перенаправление (редирект)
            messages.success(request,
                             f'Данные успешно отправлены! Ожидайте решение в письме, которое будет направлено на указанную почту - {email}!')
            return redirect(f"{request.path}?action=send")

        # Если в форме есть ошибки, заново рендерим страницу, передавая невалидную форму с ошибками
        return self.render_to_response(self.get_context_data(form=form))


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
    template_name = "webuiprojectgreenzabgu/pages/eco_habits_tracker.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoTasksTrackerView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/eco_tasks_tracker.html"

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


class EcoBonusListView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/eco_bonus_list.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EditEcoBonusView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/edit_eco_bonus.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RatingBoardView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/rating_board.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class AddEcoBonusView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/add_eco_bonus.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoTasksView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/eco_tasks.html"

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
