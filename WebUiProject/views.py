import base64
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, FormView, CreateView, ListView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy

from .forms import BlogPostForm, BlogPostImageFormSet, UserUpdateForm, UserCreateForm, ProjectForm, ProjectTypeForm
from .models import Project, Blog, BlogImage, ProjectType
from .permissions import RoleRequiredMixin

import requests
import json
from django.shortcuts import render
from django.views import View
from django.http import StreamingHttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class IndexView(View):
    template_name = "pages/index.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        return {
            'stats': {'projects': 3, 'publications': 30, 'mentors': 7},
            # 'latest_news': News.objects.all()[:3]
        }


@method_decorator(csrf_exempt, name='dispatch')
class StreamChatView(View):
    def post(self, request, *args, **kwargs):
        prompt = request.POST.get('prompt', '')
        if not prompt:
            return JsonResponse({'error': 'Пустой запрос'}, status=400)

        # Проверка наличия настроек
        try:
            api_key = settings.ANYTHINGLLM_API_KEY
            api_url = settings.ANYTHINGLLM_API_URL
            workspace = settings.ANYTHINGLLM_WORKSPACE
        except AttributeError as e:
            error_msg = f"Ошибка конфигурации сервера: отсутствует настройка {e} в settings.py"
            logger.error(error_msg)
            return JsonResponse({'error': error_msg}, status=500)

        def event_stream():
            try:
                payload = {
                    "message": prompt,
                    "mode": "chat",
                    "stream": True
                }
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                url = f"{api_url}/api/v1/workspace/{workspace}/chat"

                # Таймаут 30 секунд на соединение, 120 на чтение
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=(30, 120))

                # Если API вернуло ошибку (например 401 или 500), читаем её
                if response.status_code != 200:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get('error', error_text)
                    except:
                        pass
                    yield f"data: {json.dumps({'error': f'API Error {response.status_code}: {error_text}'})}\n\n"
                    return

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        # Проксируем данные как есть
                        yield f"{decoded_line}\n\n"

            except requests.exceptions.Timeout:
                yield f"data: {json.dumps({'error': 'Таймаут соединения с AI сервером'})}\n\n"
            except requests.exceptions.ConnectionError:
                yield f"data: {json.dumps({'error': 'Невозможно подключиться к AI серверу'})}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'error': f'Внутренняя ошибка: {str(e)}'})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


@method_decorator(csrf_exempt, name='dispatch')
class UploadFileView(View):
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'Файл не найден'}, status=400)

        try:
            api_key = settings.ANYTHINGLLM_API_KEY
            api_url = settings.ANYTHINGLLM_API_URL
            workspace = settings.ANYTHINGLLM_WORKSPACE
        except AttributeError as e:
            return JsonResponse({'error': f'Ошибка конфигурации: {e}'}, status=500)

        try:
            # 1. Загрузка
            upload_url = f"{api_url}/api/v1/document/upload"
            headers = {"Authorization": f"Bearer {api_key}"}
            files = {'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)}

            response = requests.post(upload_url, files=files, headers=headers)

            # Добавляем логирование ответа для отладки
            if response.status_code != 200:
                return JsonResponse({'error': f'Ошибка загрузки в AI: {response.text}'}, status=500)

            upload_data = response.json()

            doc_name = None
            if upload_data.get('documents'):
                doc_name = upload_data['documents'][0].get('name')

            if not doc_name:
                return JsonResponse({'error': 'Не удалось получить имя документа из ответа API'}, status=500)

            # 2. Эмбеддинг
            embed_url = f"{api_url}/api/v1/workspace/{workspace}/update-embeddings"
            embed_payload = {"adds": [doc_name]}
            requests.post(embed_url, json=embed_payload, headers=headers).raise_for_status()

            return JsonResponse({'status': 'success', 'filename': uploaded_file.name, 'doc_name': doc_name})

        except Exception as e:
            logger.error(f"Upload error: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


# Страница с проектами "projects"
class ProjectsView(TemplateView):
    template_name = "pages/projects.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = Project.objects.all()
        context["projects"] = projects
        return context


# Страница с деталями проекта по его id и данным
class ProjectDetailsView(TemplateView):
    template_name = "pages/project_details.html"
    project = None

    def get(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        self.project = Project.objects.get(pk=project_id)
        return self.render_to_response({
            'pk': project_id,
            'project': self.project,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context


# Страница об предприятии (СКБ КБ)
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
class AdminView(RoleRequiredMixin, TemplateView):
    required_roles = ['Администраторы']
    template_name = "pages/admin.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = User.objects.all().select_related()
        context["groups"] = Group.objects.all()
        context["projects"] = Project.objects.all()
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
