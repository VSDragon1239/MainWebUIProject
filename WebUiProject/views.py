import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, CreateView, ListView, UpdateView, DeleteView
from django.contrib import messages

from WebUIProjectGreenZabGU.forms import UserUpdateForm, UserCreateForm, \
    ProfileAvatarForm
from .models import Blog, UserTaskCompletion, Profile
from WebUIProjectGreenZabGU.permissions import RoleRequiredMixin

from django.shortcuts import render
from django.views import View

from WebUIProjectGreenZabGU.services import EcoCoinService

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


class EditProfileView(LoginRequiredMixin, View):
    """Вьюха для обработки ДВУХ форм одновременно"""

    def get(self, request):
        # get_or_create для защиты от отсутствия профиля
        profile, _ = Profile.objects.get_or_create(user=request.user)
        p_form = ProfileAvatarForm(instance=profile)

        context = {
            'p_form': p_form,
        }
        return render(request, 'pages/profile_edit.html', context)

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        # ВАЖНО: request.FILES обязателен для загрузки картинок!
        p_form = ProfileAvatarForm(request.POST, request.FILES, instance=profile)

        if p_form.is_valid():
            p_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')

        context = {
            'p_form': p_form,
        }
        return render(request, 'pages/profile_edit.html', context)


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
