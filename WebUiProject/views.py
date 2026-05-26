import logging

from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, CreateView, UpdateView, DeleteView
from django.contrib import messages

from WebUIProjectGreenZabGU.forms import UserUpdateForm, UserCreateForm
from .models import Blog
from WebUIProjectGreenZabGU.permissions import RoleRequiredMixin

from django.shortcuts import render

logger = logging.getLogger(__name__)


# @method_decorator(csrf_exempt, name='dispatch')
# class UploadFileView(View):
#     def post(self, request, *args, **kwargs):
#         uploaded_file = request.FILES.get('file')
#         if not uploaded_file:
#             return JsonResponse({'error': 'Файл не найден'}, status=400)
#
#         try:
#             api_key = settings.ANYTHINGLLM_API_KEY
#             api_base_url = settings.ANYTHINGLLM_API_URL.rstrip('/')
#             workspace = settings.ANYTHINGLLM_WORKSPACE
#         except AttributeError as e:
#             return JsonResponse({'error': f'Ошибка конфигурации: {e}'}, status=500)
#
#         try:
#             # 1. Загрузка документа
#             upload_url = f"{api_base_url}/api/v1/document/upload"
#             headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
#             files = {'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)}
#
#             response = requests.post(upload_url, files=files, headers=headers)
#             if response.status_code != 200:
#                 return JsonResponse({'error': f'Ошибка загрузки файла: {response.text}'}, status=500)
#
#             upload_data = response.json()
#
#             # Получаем имя документа из ответа
#             doc_name = None
#             if upload_data.get('documents'):
#                 # Пытаемся получить name, если нет - location
#                 doc_name = upload_data['documents'][0].get('name') or upload_data['documents'][0].get('location')
#
#             if not doc_name:
#                 return JsonResponse({'error': 'Не удалось получить имя документа из ответа API'}, status=500)
#
#             # 2. Добавление в Workspace (Embedding)
#             embed_url = f"{api_base_url}/api/v1/workspace/{workspace}/update-embeddings"
#             embed_payload = {"adds": [doc_name]}
#
#             response = requests.post(embed_url, json=embed_payload, headers=headers)
#             if response.status_code != 200:
#                 return JsonResponse({'error': f'Ошибка встраивания: {response.text}'}, status=500)
#
#             return JsonResponse({'status': 'success', 'filename': uploaded_file.name, 'doc_name': doc_name})
#
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

class IndexView(TemplateView):
    template_name = "webuiproject/pages/index.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blogs_list = Blog.objects.all()
        context["blogs_list"] = blogs_list
        return context


# Страница о нас
class AboutView(TemplateView):
    template_name = "pages/about.html"

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


# Страница входа (доступно только тем кто не авторизован)
class AuthView(FormView):
    template_name = "webuiproject/pages/auth.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            return redirect("/profile/")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


# Страница нет доступа (вместо ошибки 403)
class NoAccessView(TemplateView):
    template_name = "webuiproject/pages/no_access.html"

    def get(self, request, *args, **kwargs):
        # # 1. Проверяем авторизацию
        # if request.user.is_authenticated:
        #     # 2. Проверяем группу
        #     if request.user.groups.filter(name="Партнеры").exists():
        #         # 3. Перенаправляем (здесь должно быть имя из urls.py или прямой путь '/partner/')
        #         return redirect("partner_dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем простую переменную True/False в шаблон
        context['is_partner'] = self.request.user.is_authenticated and self.request.user.groups.filter(
            name="Партнеры").exists()
        return context
