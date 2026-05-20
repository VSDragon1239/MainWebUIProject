from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.utils.crypto import get_random_string

from WebUIProjectGreenZabGU.email_sender import send_templated_mail
from .models import ProjectType, Project, Blog, BlogImage, EcoTask, UserTaskCompletion, EcoCoinTransaction, \
    EcoHabitCategory, EcoHabit, RegistrationRequest, Profile


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "start_date", "end_date")
    list_filter = ("type",)
    filter_horizontal = ("leaders", "members")


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "author_id", "created_at", "updated_at", "content")


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    list_display = ("blog", "caption")


@admin.register(EcoTask)
class EcoTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'reward', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)


@admin.register(UserTaskCompletion)
class UserTaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'completed_at')
    readonly_fields = ('user', 'task', 'completed_at')

    @admin.register(EcoHabitCategory)
    class EcoHabitCategoryAdmin(admin.ModelAdmin):
        list_display = ('name', 'icon')
        prepopulated_fields = {}  # Если захотите добавить slug

    @admin.register(EcoHabit)
    class EcoHabitAdmin(admin.ModelAdmin):
        list_display = ('title', 'category', 'base_reward', 'streak_bonus', 'is_active')
        list_filter = ('category', 'is_active')


# @admin.register(RegistrationRequest)
# class RegistrationRequestAdmin(admin.ModelAdmin):
#     list_display = ('fio', 'group', 'email', 'created_at', 'status')
#     list_filter = ('status',)
#     search_fields = ('fio', 'email', 'group')
#     list_editable = ('status',)

# @admin.register(RegistrationRequest)
# class RegistrationRequestAdmin(admin.ModelAdmin):
#     list_display = ('fio', 'group', 'email', 'created_at', 'status')
#     list_filter = ('status',)
#     search_fields = ('fio', 'email', 'group')
#     list_editable = ('status',)
#     readonly_fields = ('fio', 'group', 'phone', 'email', 'created_at')
#
#     def save_model(self, request, obj, form, change):
#         # Если это редактирование (а не создание новой)
#         if change:
#             # Достаем старое значение из БД ДО сохранения
#             old_obj = RegistrationRequest.objects.get(pk=obj.pk)
#
#             # Если статус изменился
#             if old_obj.status != obj.status:
#                 is_approved = obj.status == "approved"
#
#                 # Формируем ссылку на логин (подставьте свой домен)
#                 login_url = "https://ваш-домен.ru/login/"
#
#                 # Отправляем письмо (Сценарий 2)
#                 send_templated_mail(
#                     subject=f"Результат заявки в Green ZabGu: {'Одобрено' if is_approved else 'Отклонено'}",
#                     template_path="webuiprojectgreenzabgu/emails/registration_result.html",
#                     context_dict={
#                         "fio": obj.fio,
#                         "is_approved": is_approved,
#                         "login_url": login_url
#                     },
#                     to_email=obj.email
#                 )
#
#         # Сохраняем объект
#         super().save_model(request, obj, form, change)


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('fio', 'group', 'email', 'created_at', 'status')
    list_filter = ('status',)
    search_fields = ('fio', 'email', 'group')
    list_editable = ('status',)
    readonly_fields = ('fio', 'group', 'phone', 'email', 'created_at')

    def save_model(self, request, obj, form, change):
        # Срабатывает ТОЛЬКО при редактировании (не при создании новой заявки)
        if change:
            # Достаем старое значение из БД до сохранения
            old_obj = RegistrationRequest.objects.get(pk=obj.pk)

            # Если статус изменился на "Одобрена"
            if old_obj.status != obj.status and obj.status == "approved":
                email = obj.email

                # Защита от дублей: если юзер с таким email уже есть (например, одобрили дважды)
                if not User.objects.filter(username=email).exists():

                    # 1. Генерируем надежный пароль
                    raw_password = get_random_string(length=12,
                                                     allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')

                    # 2. Разбиваем ФИО (предполагаем формат "Иванов Иван Иванович")
                    fio_parts = obj.fio.split()
                    last_name = fio_parts[0] if len(fio_parts) > 0 else ""
                    first_name = fio_parts[1] if len(fio_parts) > 1 else ""

                    # 3. Создаем пользователя (username = email)
                    new_user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=raw_password,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True
                    )

                    # 4. Создаем пустой профиль для него
                    Profile.objects.create(user=new_user)

                    # 5. Добавляем в базовую группу "Участники"
                    try:
                        default_group = Group.objects.get(name='Участники')
                        new_user.groups.add(default_group)
                    except Group.DoesNotExist:
                        pass  # Если группы нет, просто пропускаем (залогируйте это в реальном проекте)

                    # 6. Отправляем письмо с данными для входа
                    send_templated_mail(
                        subject="Доступ к порталу Green ZabGu открыт",
                        template_path="webuiprojectgreenzabgu/emails/registration_approved.html",
                        context_dict={
                            "fio": obj.fio,
                            "username": email,
                            "password": raw_password,
                            "login_url": "https://localhost/main/green-zabgu/profile/"  # ЗАМЕНИТЕ НА СВОЙ ДОМЕН
                        },
                        to_email=email
                    )

            # Если статус изменился на "Отклонена"
            elif old_obj.status != obj.status and obj.status == "rejected":
                send_templated_mail(
                    subject="Заявка в Green ZabGu отклонена",
                    template_path="webuiprojectgreenzabgu/emails/registration_rejected.html",
                    context_dict={"fio": obj.fio},
                    to_email=obj.email
                )

        # Сохраняем саму заявку (меняем статус в БД)
        super().save_model(request, obj, form, change)
