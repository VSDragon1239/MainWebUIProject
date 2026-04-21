# import base64
import logging
from datetime import datetime

# import os
# import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, FormView, CreateView, ListView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404

from .forms import BlogPostForm, BlogPostImageFormSet, UserUpdateForm, UserCreateForm, ProjectForm, ProjectTypeForm
from .models import Project, Blog, BlogImage, ProjectType, EcoTransactionType, EcoTask, UserTaskCompletion
from .permissions import RoleRequiredMixin

import requests
# import json
from django.shortcuts import render
from django.views import View
# from django.http import StreamingHttpResponse
from django.conf import settings

from .services import EcoCoinService

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    template_name = "pages/index.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blogs_list = Blog.objects.all()
        context["blogs_list"] = blogs_list
        return context


# class RagChatBotView(TemplateView):
#     template_name = "pages/chatbot.html"
#
#     def get(self, request, *args, **kwargs):
#         context = self.get_context_data()
#         return render(request, self.template_name, context)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         blogs_list = Blog.objects.all()
#         context["blogs_list"] = blogs_list
#         return context


# @method_decorator(csrf_exempt, name='dispatch')
# class StreamChatView(View):
#     def post(self, request, *args, **kwargs):
#         prompt = request.POST.get('prompt', '')
#
#         if not prompt:
#             return JsonResponse({'error': 'Пустой запрос'}, status=400)
#
#         # Проверка настроек
#         try:
#             api_key = settings.ANYTHINGLLM_API_KEY
#             api_base_url = settings.ANYTHINGLLM_API_URL.rstrip('/')  # Убираем слэш в конце
#             workspace = settings.ANYTHINGLLM_WORKSPACE
#         except AttributeError as e:
#             err_msg = f"Ошибка конфигурации: в settings.py не найдена переменная {e}"
#             logger.error(err_msg)
#             return JsonResponse({'error': err_msg}, status=500)
#
#         def event_stream():
#             try:
#                 # ПРАВИЛЬНЫЙ ЭНДПОИНТ ИЗ ДОКУМЕНТАЦИИ
#                 url = f"{api_base_url}/api/v1/workspace/{workspace}/stream-chat"
#
#                 payload = {
#                     "message": prompt,
#                     "mode": "chat"
#                 }
#                 headers = {
#                     "Authorization": f"Bearer {api_key}",
#                     "Content-Type": "application/json"
#                 }
#
#                 # Выполняем запрос к AnythingLLM
#                 response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
#
#                 # Если API вернуло ошибку (не 200)
#                 if response.status_code != 200:
#                     error_text = response.text
#                     try:
#                         error_json = response.json()
#                         error_text = error_json.get('error', error_text)
#                     except:
#                         pass
#                     yield f"data: {json.dumps({'error': f'API Error {response.status_code}: {error_text}'})}\n\n"
#                     return
#
#                 # Читаем поток и передаем его клиенту
#                 for line in response.iter_lines():
#                     if line:
#                         decoded_line = line.decode('utf-8')
#                         # AnythingLLM присылает данные в формате: "data: {...}"
#                         yield f"{decoded_line}\n\n"
#
#             except requests.exceptions.ConnectionError:
#                 yield f"data: {json.dumps({'error': 'Невозможно подключиться к AnythingLLM серверу'})}\n\n"
#             except Exception as e:
#                 logger.error(f"Stream error: {str(e)}", exc_info=True)
#                 yield f"data: {json.dumps({'error': f'Внутренняя ошибка сервера: {str(e)}'})}\n\n"
#
#         return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


@method_decorator(csrf_exempt, name='dispatch')
class UploadFileView(View):
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'Файл не найден'}, status=400)

        try:
            api_key = settings.ANYTHINGLLM_API_KEY
            api_base_url = settings.ANYTHINGLLM_API_URL.rstrip('/')
            workspace = settings.ANYTHINGLLM_WORKSPACE
        except AttributeError as e:
            return JsonResponse({'error': f'Ошибка конфигурации: {e}'}, status=500)

        try:
            # 1. Загрузка документа
            upload_url = f"{api_base_url}/api/v1/document/upload"
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
            files = {'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)}

            response = requests.post(upload_url, files=files, headers=headers)
            if response.status_code != 200:
                return JsonResponse({'error': f'Ошибка загрузки файла: {response.text}'}, status=500)

            upload_data = response.json()

            # Получаем имя документа из ответа
            doc_name = None
            if upload_data.get('documents'):
                # Пытаемся получить name, если нет - location
                doc_name = upload_data['documents'][0].get('name') or upload_data['documents'][0].get('location')

            if not doc_name:
                return JsonResponse({'error': 'Не удалось получить имя документа из ответа API'}, status=500)

            # 2. Добавление в Workspace (Embedding)
            embed_url = f"{api_base_url}/api/v1/workspace/{workspace}/update-embeddings"
            embed_payload = {"adds": [doc_name]}

            response = requests.post(embed_url, json=embed_payload, headers=headers)
            if response.status_code != 200:
                return JsonResponse({'error': f'Ошибка встраивания: {response.text}'}, status=500)

            return JsonResponse({'status': 'success', 'filename': uploaded_file.name, 'doc_name': doc_name})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# Страница с проектами "projects"
# class ProjectsView(TemplateView):
#     template_name = "pages/projects.html"
#
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         projects = Project.objects.all()
#         context["projects"] = projects
#         return context


# Страница с деталями проекта по его id и данным
# class ProjectDetailsView(TemplateView):
#     template_name = "pages/project_details.html"
#     project = None
#
#     def get(self, request, *args, **kwargs):
#         project_id = kwargs.get('pk')
#         self.project = Project.objects.get(pk=project_id)
#         return self.render_to_response({
#             'pk': project_id,
#             'project': self.project,
#         })
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["project"] = self.project
#         return context


# Страница об предприятии
class AboutView(TemplateView):
    template_name = "pages/about.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Контактная информация
class ContactsView(TemplateView):
    template_name = "pages/contacts.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Области применения
class ApplicationsView(TemplateView):
    template_name = "pages/applications.html"

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


# Другая страница
class OtherView(TemplateView):
    template_name = "pages/other.html"

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
    template_name = "pages/profile.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        context['user'] = user

        # 1. Баланс пользователя
        context['eco_balance'] = EcoCoinService.get_balance(user)

        # 2. Выполненные задания (сортируем от новых к старым)
        # select_related('task') забирает данные о самом задании одним запросом (оптимизация)
        context['completed_tasks'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('-completed_at')

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


class UserCreateView(RoleRequiredMixin, CreateView):
    required_roles = ['Администраторы', "Руководители"]
    template_name = "accounts/user_create_form.html"
    form_class = UserCreateForm
    model = User
    success_url = reverse_lazy("admin")

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["groups"] = Group.objects.all()
        return context


class ProjectTypeCreateView(RoleRequiredMixin, CreateView):
    required_roles = ['Администраторы']
    model = ProjectType
    form_class = ProjectTypeForm
    template_name = "projects/project_type_create_form.html"  # не обязателен, будем бить через AJAX

    def form_valid(self, form):
        obj = form.save()
        # если AJAX — возвращаем JSON, иначе редирект
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"id": obj.pk, "name": obj.name}, status=201)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ProjectCreateView(RoleRequiredMixin, CreateView):
    required_roles = ['Администраторы']
    template_name = "projects/project_create_form.html"
    form_class = ProjectForm
    model = Project
    success_url = reverse_lazy("admin")

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ProjectUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ['Администраторы', "Руководители"]
    model = Project
    form_class = ProjectForm
    template_name = "projects/project__update_form.html"
    success_url = reverse_lazy("admin")

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ProjectsDeleteView(RoleRequiredMixin, UpdateView):
    required_roles = ['Администраторы', "Руководители"]
    model = Project
    form_class = ProjectForm
    template_name = "projects/project__update_form.html"
    success_url = reverse_lazy("admin")

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class UserUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ['Администраторы']
    template_name = "accounts/user_update_form.html"
    model = User
    form_class = UserUpdateForm
    success_url = reverse_lazy("admin")

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class UserDeleteView(RoleRequiredMixin, DeleteView):
    required_roles = ['Администраторы']
    model = User
    template_name = "accounts/user_confirm_delete.html"
    success_url = reverse_lazy("admin")

    # Ничего не трогаем в get(): DeleteView сам отдаст object в шаблон

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Для красивого отображения ролей в шаблоне:
        context["user_groups"] = self.object.groups.all()
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # 1) нельзя удалить самого себя (удобнее с сообщением, а не 404)
        if self.object.pk == request.user.pk:
            messages.error(request, "Нельзя удалить собственный аккаунт.")
            return redirect(self.get_success_url())

        # 2) нельзя удалить последнего суперпользователя
        if self.object.is_superuser:
            others = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=self.object.pk).count()
            if others == 0:
                messages.error(request, "Нельзя удалить последнего суперпользователя.")
                return redirect(self.get_success_url())

        # 3) нельзя удалить последнего «Администратора» (по группе)
        if self.object.groups.filter(name="Администраторы").exists():
            others_admins = (
                User.objects
                .filter(groups__name="Администраторы", is_active=True)
                .exclude(pk=self.object.pk)
                .distinct()
                .count()
            )
            if others_admins == 0:
                messages.error(request, "Нельзя удалить последнего администратора.")
                return redirect(self.get_success_url())

        username = self.object.get_username()
        resp = super().delete(request, *args, **kwargs)
        messages.success(request, f"Пользователь «{username}» удалён.")
        return resp


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


# Страница входа (доступно только тем кто не авторизован)
class AuthView(FormView):
    template_name = "pages/auth.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            return redirect("/profile/")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# Страница нет доступа (вместо ошибки 403)
class NoAccessView(TemplateView):
    template_name = "pages/no_access.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


# class BlenderWorkspaceView(TemplateView):
#     template_name = "pages/blender_workspace.html"
#
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         return context


# class BlenderStartView(View):
#     def post(self, request):
#         client = docker.from_env()
#
#         # Генерируем уникальный порт (или используем случайный свободный)
#         # Для простоты примера возьмем диапазон 6901-6999, но лучше проверять занятость
#         # В продакшне лучше использовать Docker API для автоматического назначения порта
#         host_port = 6901
#         container_name = f"blender_user_{request.user.id}_{uuid.uuid4().hex[:6]}"
#
#         # Пароль для сессии KasmVNC
#         vnc_password = "secure_password_123"
#
#         try:
#             container = client.containers.run(
#                 # image="kasmweb/blender:latest",
#                 # image="kasmweb/chrome:1.15.0",
#                 image="my-blender-image",  # Имя вашего собранного образа
#                 name=container_name,
#                 environment={"VNC_PW": vnc_password},
#                 ports={'6901/tcp': None},
#                 detach=True,
#                 remove=True,
#                 shm_size="512m",
#                 # Важно для производительности Blender:
#                 runtime="nvidia"  # Раскомментировать, если есть NVIDIA GPU на сервере
#             )
#
#             # URL, по которому Nginx проксирует к этому порту
#             # Структура URL будет описана в Nginx на следующем этапе
#             iframe_url = f"https://{request.get_host()}/kasm-session/{host_port}/"
#
#             return JsonResponse({
#                 'status': 'success',
#                 'iframe_url': iframe_url,
#                 'password': vnc_password  # В реальном приложении пароль лучше не отдавать, если включен SSO
#             })
#
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# class BlenderStartView(View):
#     def post(self, request):
#         client = docker.from_env()
#         container_name = f"blender_user_{request.user.id}_{uuid.uuid4().hex[:6]}"
#         vnc_password = "password"
#
#         try:
#             # 1. Запускаем контейнер
#             container = client.containers.run(
#                 image="my-blender-image",  # Имя вашего собранного образа
#                 name=container_name,
#                 environment={
#                     "VNC_PW": vnc_password,
#                     # ГЛАВНОЕ ИСПРАВЛЕНИЕ:
#                     # Отключаем HTTPS внутри Kasm, чтобы Nginx мог проксировать HTTP
#                     "VNC_DISABLE_HTTPS": "1",
#                 },
#                 # Автоматический выбор свободного порта
#                 ports={'6901/tcp': None},
#                 detach=True,
#                 remove=True,
#                 shm_size="512m"
#             )
#
#             # 2. Получаем динамический порт
#             container.reload()
#             ports_info = container.attrs['NetworkSettings']['Ports']['6901/tcp']
#             host_port = ports_info[0]['HostPort']
#
#             # 3. Формируем URL (Nginx проксирует HTTP, браузер видит HTTPS)
#             iframe_url = f"https://{request.get_host()}/kasm-session/{host_port}/"
#
#             return JsonResponse({
#                 'status': 'success',
#                 'iframe_url': iframe_url,
#                 'password': vnc_password
#             })
#
#         except Exception as e:
#             print(f"DOCKER ERROR: {str(e)}")
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# class BlenderStartView(View):
#     def post(self, request):
#         password = os.getenv('MY_WORKSPACE_PASSWORD', 'default_password')
#         # Просто возвращаем статичный URL нашего сервиса
#         # iframe_url = f"https://{request.get_host()}/lxdesk/"
#         iframe_url = f"https://194.87.214.67:8443/lxdesk/"
#         return JsonResponse({
#             'status': 'success',
#             'iframe_url': iframe_url,
#             'password': password
#         })
#         # return JsonResponse({
#         #     'status': 'success',
#         #     'iframe_url': 'https://194.87.214.67:8083/',
#         #     'password': ''
#         # })


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


class EcoHabitsCategoriesView(TemplateView):
    template_name = "pages/eco_habits_categories.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoHabitsView(TemplateView):
    template_name = "pages/eco_habits.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EcoHabitDetailsView(TemplateView):
    template_name = "pages/eco_habit_details.html"

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

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #
    #     # Берем только активные задания
    #     tasks = EcoTask.objects.filter(is_active=True)
    #
    #     # Получаем ID заданий, которые ТЕКУЩИЙ пользователь уже выполнил
    #     completed_ids = UserTaskCompletion.objects.filter(
    #         user=self.request.user
    #     ).values_list('task_id', flat=True)
    #
    #     context['tasks'] = tasks
    #     context['completed_task_ids'] = set(completed_ids)  # Используем set для быстрого поиска в шаблоне
    #
    #     return context


class EcoTaskDetailsView(LoginRequiredMixin, DetailView):   # DetailView от Django — он сам найдет задачу в БД по ID из URL или выдаст красивую ошибку 404, если задача не существует.
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


class EcoTaskDetailsView(TemplateView):
    template_name = "pages/eco_task_details.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


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
