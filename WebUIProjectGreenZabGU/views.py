import logging
import uuid
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import Http404

from MainWebUIProject import settings
from .email_sender import send_templated_mail
from .forms import BlogPostForm, BlogPostImageFormSet, RegistrationRequestForm, ProfileAvatarForm, UserEditForm, \
    OfferCreateForm
from WebUiProject.models import Project, Blog, EcoTransactionType, EcoTask, UserTaskCompletion, \
    EcoHabit, UserHabitLog, EcoHabitCategory, Profile, RegistrationRequest, EcoCoinTransaction, Event, EventCategory, \
    UserPromoCode, Offer
from .permissions import RoleRequiredMixin, PartnerRequiredMixin

from django.views import View

from .services import EcoCoinService, process_registration_approval, InsufficientFundsError, \
    process_registration_rejection

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
    template_name = "webuiprojectgreenzabgu/profile/profile.html"

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
        eco_balance = EcoCoinService.get_balance(user)
        context['eco_balance'] = eco_balance

        # --- НОВОЕ: Геймификация (Уровень и прогресс) ---
        # Простая формула: 1 уровень = 100 ECO. Можно усложнить потом.
        context['level'] = (eco_balance // 100) + 1
        context['progress_percent'] = eco_balance % 100

        # --- НОВОЕ: Статистика ---
        context['completed_tasks_count'] = UserTaskCompletion.objects.filter(user=user).count()

        # Считаем максимальную серию из логов привычек
        max_streak = UserHabitLog.objects.filter(user=user).aggregate(max_streak=Max('streak_count'))['max_streak']
        context['max_streak'] = max_streak if max_streak else 0

        # --- НОВОЕ: Последняя активность (из транзакций) ---
        # Берем 5 последних транзакций для ленты
        context['recent_transactions'] = EcoCoinTransaction.objects.filter(
            wallet__user=user
        ).order_by('-created_at')[:5]

        # Выполненные задания (если нужны где-то еще)
        context['completed_tasks'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('-completed_at')

        # Роли
        roles_priority = {
            'Администраторы': ('Администратор', 'danger'),
            'Контент менеджер': ('Контент-менеджер', 'info'),
            'Руководители': ('Руководитель', 'warning'),
            'Участники': ('Участник', 'secondary'),
        }
        user_groups = user.groups.values_list('name', flat=True)
        context['display_role'] = ('Без роли', 'light')

        for group_name in user_groups:
            if group_name in roles_priority:
                context['display_role'] = roles_priority[group_name]
                break

        return context


class EditProfileView(LoginRequiredMixin, View):
    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        u_form = UserEditForm(instance=request.user)
        p_form = ProfileAvatarForm(instance=profile)

        context = {
            'u_form': u_form,
            'p_form': p_form,
        }
        return render(request, 'webuiprojectgreenzabgu/profile/profile_edit.html', context)

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        u_form = UserEditForm(request.POST, instance=request.user)
        # ВАЖНО: request.FILES для аватарки!
        p_form = ProfileAvatarForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            with db_transaction.atomic():
                u_form.save()
                p_form.save()
            messages.success(request, 'Ваши данные успешно обновлены!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')

        context = {
            'u_form': u_form,
            'p_form': p_form,
        }
        return render(request, 'webuiprojectgreenzabgu/profile/profile_edit.html', context)


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

        # НОВОЕ: Запросы на регистрацию (сначала новые)
        context["requests"] = RegistrationRequest.objects.all().order_by('-created_at')

        # НОВОЕ: Статистика в цифрах
        counts = RegistrationRequest.objects.values('status').annotate(count=Count('id'))
        stats_dict = {item['status']: item['count'] for item in counts}

        context["stats"] = {
            "new": stats_dict.get('new', 0),
            "approved": stats_dict.get('approved', 0),
            "rejected": stats_dict.get('rejected', 0),
            "total": sum(stats_dict.values())
        }

        return context


# Управляет заявками
class ModerateRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            req = RegistrationRequest.objects.get(pk=pk)
        except RegistrationRequest.DoesNotExist:
            return JsonResponse({"error": "Заявка не найдена"}, status=404)

        action = request.POST.get("action")

        if action == "approve":
            success, result = process_registration_approval(req)
            if success:
                return JsonResponse({"status": "success", "message": "Пользователь создан, пароль отправлен"})
            else:
                return JsonResponse({"status": "error", "message": result}, status=400)


        elif action == "reject":
            success, result = process_registration_rejection(req)
            if success:
                return JsonResponse({"status": "success", "message": result})
            else:
                return JsonResponse({"status": "error", "message": result}, status=400)
        return JsonResponse({"error": "Неверный action"}, status=400)


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


# ==========================================
# 1. СОБЫТИЯ
# ==========================================

class CategoriesEventsView(ListView):
    """Список категорий мероприятий"""
    model = EventCategory
    template_name = "webuiprojectgreenzabgu/events/categories_events.html"
    context_object_name = 'categories'


class EventsView(ListView):
    """Список мероприятий внутри категории"""
    model = Event
    template_name = "webuiprojectgreenzabgu/events/events.html"
    context_object_name = 'events'

    def get_queryset(self):
        category_id = self.kwargs.get('pk')
        return Event.objects.filter(category_id=category_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_id = self.kwargs.get('pk')

        # Безопасное получение категории без вызова ошибки 404
        context['category'] = EventCategory.objects.filter(pk=category_id).first()

        return context


class EventDetailsView(DetailView):
    """Детальная страница конкретного мероприятия"""
    model = Event
    template_name = "webuiprojectgreenzabgu/events/event_details.html"
    context_object_name = 'event'

    # ИСПРАВЛЕНИЕ: Извлекаем pk2 из URL
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        pk = self.kwargs.get('pk2')  # Берем второй параметр из URL
        queryset = queryset.filter(pk=pk)
        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("Мероприятие не найдено")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем категорию для хлебных крошек
        context['category'] = self.object.category
        return context


class EcoHabitsTrackerView(LoginRequiredMixin, TemplateView):
    """
    Теперь это не пустая страница, а Главный Дашборд Привычек.
    Отсюда пользователь идет к категориям.
    """
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получаем все категории, в которых есть привычки
        context['categories'] = EcoHabitCategory.objects.filter(habits__is_active=True).distinct()

        # Считаем общую статистику для карточек на дашборде
        from django.db.models import Max, Count
        stats = UserHabitLog.objects.filter(user=user).aggregate(
            total_logs=Count('id'),
            max_streak=Max('streak_count')
        )
        context['total_habits_done'] = stats['total_logs'] or 0
        context['best_streak'] = stats['max_streak'] or 0

        return context


class EcoTasksTrackerView(LoginRequiredMixin, TemplateView):
    template_name = "webuiprojectgreenzabgu/tasks/eco_tasks_tracker.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Доступные (невыполненные) задания
        completed_ids = UserTaskCompletion.objects.filter(user=user).values_list('task_id', flat=True)
        available_tasks = EcoTask.objects.filter(is_active=True).exclude(pk__in=completed_ids)
        context['tasks'] = available_tasks

        # 2. Статистика для верхней зеленой плашки
        context['total_completed'] = UserTaskCompletion.objects.filter(user=user).count()
        context['active_tasks_count'] = available_tasks.count()

        # 3. Последние 5 выполненных заданий (для истории внизу)
        context['recent_completions'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('-completed_at')[:5]

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


# class EcoTasksView(TemplateView):
#     template_name = "webuiprojectgreenzabgu/pages/eco_tasks.html"
#
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         completed_ids = UserTaskCompletion.objects.filter(
#             user=self.request.user
#         ).values_list('task_id', flat=True)
#
#         # 2. Выводим ТОЛЬКО те активные задания, которых НЕТ в списке выполненных
#         tasks = EcoTask.objects.filter(is_active=True).exclude(pk__in=completed_ids)
#
#         context['tasks'] = tasks
#         context['completed_task_ids'] = set(completed_ids)
#         return context


class EcoTaskDetailsView(LoginRequiredMixin,
                         DetailView):  # DetailView от Django — он сам найдет задачу в БД по ID из URL или выдаст красивую ошибку 404, если задача не существует.
    """Детальная страница конкретного задания"""
    model = EcoTask
    template_name = "webuiprojectgreenzabgu/tasks/eco_task_details.html"
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
    def post(self, request, task_id):
        task = get_object_or_404(EcoTask, pk=task_id, is_active=True)

        # Формируем уникальный ключ
        external_id = f"task:{task.id}:user:{request.user.id}"
        task_type_code = task.task_type.code if task.task_type else 'trust'

        proof_text = ""
        proof_image = None

        # 1. Валидация типа
        if task_type_code == 'text_code':
            proof_text = request.POST.get('proof_text', '').strip()
            if not proof_text:
                return JsonResponse({"error": "Введите код для подтверждения"}, status=400)

            if task.secret_code:
                if proof_text.upper() != task.secret_code.upper():
                    return JsonResponse({"error": "Неверный код! Проверьте данные и попробуйте снова."}, status=400)

        elif task_type_code == 'photo':
            if 'proof_image' not in request.FILES:
                return JsonResponse({"error": "Прикрепите фотографию"}, status=400)
            proof_image = request.FILES['proof_image']

        # 2. ЯВНАЯ ПРОВЕРКА: Была ли уже попытка выполнить это задание?
        if UserTaskCompletion.objects.filter(user=request.user, task=task).exists():
            return JsonResponse({"error": "Вы уже выполнили это задание"}, status=400)

        # 3. ЯВНАЯ ПРОВЕРКА: Завис ли этот external_id в логах транзакций? (Защита от "призраков")
        if EcoCoinTransaction.objects.filter(external_id=external_id).exists():
            return JsonResponse({
                "error": "Система уже зафиксировала выполнение этого задания ранее (транзакция существует, но статус мог не обновиться)."
            }, status=400)

        try:
            with db_transaction.atomic():
                new_balance = EcoCoinService.credit(
                    user=request.user,
                    amount=task.reward,
                    tx_type=EcoTransactionType.TASK_COMPLETED,
                    external_id=external_id
                )

                UserTaskCompletion.objects.create(
                    user=request.user,
                    task=task,
                    proof_text=proof_text,
                    proof_image=proof_image
                )

            return JsonResponse({
                "status": "success",
                "message": f"+{task.reward} ECO получено!",
                "new_balance": str(new_balance)
            })


        except IntegrityError as e:
            import logging
            logger = logging.getLogger(__name__)
            # Точная проверка: из-за какого именно поля упала база данных?
            error_msg = str(e)

            if "external_id" in error_msg or "tx_type" in error_msg:
                # Ситуация: Транзакция начисления баллов уже ЕСТЬ в базе, а UserTaskCompletion почему-то нет.
                # Чтобы починить этот сбой ("призрак"), мы прямо здесь досоздаем объект выполнения:
                try:
                    UserTaskCompletion.objects.create(
                        user=request.user,
                        task=task,
                        proof_text=proof_text,
                        proof_image=proof_image
                    )
                    actual_balance = EcoCoinService.get_balance(request.user)
                    return JsonResponse({
                        "status": "success",
                        "message": "Задание успешно синхронизировано и выполнено!",
                        "new_balance": str(actual_balance)
                    })
                except Exception as inner_e:
                    return JsonResponse({"error": f"Это задание уже было обработано системой ранее."}, status=400)

            # Если это действительно Race Condition (запись UserTaskCompletion заблокировала уникальный индекс)
            task_already_done = UserTaskCompletion.objects.filter(user=request.user, task=task).exists()
            if task_already_done:
                actual_balance = EcoCoinService.get_balance(request.user)
                return JsonResponse({
                    "status": "success",
                    "message": "Задание выполнено!",
                    "new_balance": str(actual_balance)
                })

            # Любая другая непредвиденная ошибка уникальности
            logger.warning(f"IntegrityError во вьюхе тасок: {error_msg}")
            return JsonResponse({
                "error": f"Ошибка базы данных (IntegrityError): {error_msg}. Проверьте уникальность индексов."
            }, status=400)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Critical error completing task {task_id}: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"Ошибка сервера: {str(e)}"}, status=500)


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
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits_categories.html"
    context_object_name = 'categories'

    def get_queryset(self):
        # Скрываем категории, в которых нет ни одной активной привычки
        return EcoHabitCategory.objects.filter(habits__is_active=True).distinct()


class EcoHabitsView(LoginRequiredMixin, ListView):
    """Список привычек внутри конкретной категории"""
    model = EcoHabit
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits.html"
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
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habit_details.html"
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


class MarketplaceView(LoginRequiredMixin, ListView):
    """Витрина маркетплейса"""
    model = Offer
    template_name = "webuiprojectgreenzabgu/marketplace/marketplace.html"
    context_object_name = 'offers'

    def get_queryset(self):
        return Offer.objects.filter(is_active=True).select_related('partner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем активные промокоды пользователя для нижнего блока
        context['my_promocodes'] = UserPromoCode.objects.filter(
            user=self.request.user,
            is_used=False
        ).select_related('offer__partner').order_by('-created_at')
        return context


class ExchangeOfferView(LoginRequiredMixin, View):
    """AJAX обмен ECO-коинов на промокод"""

    def post(self, request, pk):
        offer = get_object_or_404(Offer, pk=pk, is_active=True)
        user = request.user

        # Формируем уникальный код (например: ECO-1A2B3C4D)
        external_id = f"exchange_offer:{offer.id}:user:{user.id}"

        try:
            with db_transaction.atomic():
                # 1. Списываем монеты
                new_balance = EcoCoinService.debit(
                    user=user,
                    amount=offer.price_in_eco,
                    tx_type=EcoTransactionType.SHOP_PURCHASE,
                    external_id=external_id
                )

                # 2. Генерируем промокод
                promo_code = f"ECO-{uuid.uuid4().hex[:8].upper()}"

                # 3. Сохраняем промокод
                UserPromoCode.objects.create(
                    user=user,
                    offer=offer,
                    code=promo_code
                )

            return JsonResponse({
                "status": "success",
                "message": f"Успешно приобретено: {offer.title}",
                "promo_code": promo_code,
                "partner_name": offer.partner.name,
                "new_balance": str(new_balance)
            })

        except InsufficientFundsError:
            return JsonResponse({"error": "Недостаточно ECO-коинов для обмена"}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Exchange error: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Ошибка сервера"}, status=500)


class PartnerDashboardView(PartnerRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "webuiprojectgreenzabgu/partner/partner_dashboard.html"
    required_roles = ['Спонсоры']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        partner = self.request.user.partner_profile.partner

        # Агрегация статистики по офферам текущего партнера
        offers_stats = UserPromoCode.objects.filter(offer__partner=partner).aggregate(
            total_issued=Count('id'),
            total_used=Count('id', filter=Q(is_used=True))
        )

        # Считаем уникальных клиентов (у которых есть хотя бы 1 не использованный промокод)
        active_clients = UserPromoCode.objects.filter(
            offer__partner=partner,
            is_used=False
        ).values('user').distinct().count()

        context['partner'] = partner
        context['joined_at'] = self.request.user.partner_profile.joined_at
        context['total_issued'] = offers_stats['total_issued'] or 0
        context['total_used'] = offers_stats['total_used'] or 0
        context['active_clients'] = active_clients

        # Последние 3 промокода для отображения на дашборде
        context['recent_promos'] = Offer.objects.filter(partner=partner).order_by('-id')[:3]

        return context


class PartnerOfferListView(PartnerRequiredMixin, RoleRequiredMixin, ListView):
    template_name = "webuiprojectgreenzabgu/partner/partner_offers.html"
    required_roles = ['Спонсоры']
    context_object_name = 'offers'

    def get_queryset(self):
        return Offer.objects.filter(partner=self.request.user.partner_profile.partner).order_by('-id')


class PartnerOfferCreateView(PartnerRequiredMixin, RoleRequiredMixin, CreateView):
    template_name = "webuiprojectgreenzabgu/partner/partner_offer_create.html"
    required_roles = ['Спонсоры']
    form_class = OfferCreateForm
    model = Offer
    success_url = reverse_lazy('partner_offers')

    def form_valid(self, form):
        form.instance.partner = self.request.user.partner_profile.partner
        form.instance.is_active = True
        messages.success(self.request, "Предложение успешно создано!")
        return super().form_valid(form)
