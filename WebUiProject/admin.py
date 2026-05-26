from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.core.checks import messages
from django.shortcuts import redirect
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from WebUIProjectGreenZabGU.services import process_registration_approval, EcoCoinService, \
    process_registration_rejection
from .models import ProjectType, Project, Blog, BlogImage, EcoTask, UserTaskCompletion, \
    EcoHabitCategory, EcoHabit, RegistrationRequest, EventCategory, Event, EcoTaskType, Partner, Offer, \
    UserPromoCode


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


# Создайте типы вручную через админку или фикстуры:
# code: 'trust', name: 'Честное слово (без проверки)'
# code: 'text_code', name: 'Ввод текста / QR-кода'
# code: 'photo', name: 'Фотоподтверждение'

admin.site.register(EcoTaskType)


@admin.register(UserTaskCompletion)
class UserTaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'completed_at', 'status', 'proof_text', 'has_proof_image')
    list_filter = ('status', 'task__task_type')
    search_fields = ('user__username', 'task__title')
    readonly_fields = ('user', 'task', 'completed_at', 'proof_text', 'proof_image', 'status')

    # 1. ЗАПРЕЩАЕМ физическое удаление!
    def has_delete_permission(self, request, obj=None):
        return False

    # 2. Добавляем кастомные действия (Actions)
    @admin.action(description='Отменить выполнение и списать ECO (выбранные)')
    def cancel_and_revoke_coins(self, request, queryset):
        # Фильтруем только те, которые еще активны
        active_completions = queryset.filter(status='active')
        success_count = 0

        for comp in active_completions:
            try:
                success, msg = EcoCoinService.reverse_task_completion(comp.user, comp)
                if success:
                    success_count += 1
            except Exception as e:
                self.message_user(request, f"Ошибка у {comp.user.username}: {str(e)}", level=messages.ERROR)

        if success_count > 0:
            self.message_user(request, f"Успешно отменено заданий: {success_count}. Монеты списаны.",
                              level=messages.SUCCESS)

    actions = [cancel_and_revoke_coins]

    # 3. Добавляем кнопку прямо на страницу редактирования одного задания
    change_form_template = "admin/user_task_completion_change_form.html"

    def response_change(self, request, obj):
        if "_cancel_task" in request.POST:
            try:
                success, msg = EcoCoinService.reverse_task_completion(obj.user, obj)
                if success:
                    self.message_user(request, msg, level=messages.SUCCESS)
                else:
                    self.message_user(request, msg, level=messages.WARNING)
            except Exception as e:
                self.message_user(request, f"Ошибка: {str(e)}", level=messages.ERROR)
            return redirect("..")  # Возвращаем к списку
        return super().response_change(request, obj)

    def has_proof_image(self, obj):
        return bool(obj.proof_image)

    has_proof_image.boolean = True
    has_proof_image.short_description = "Фото?"


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
        if change:
            old_obj = RegistrationRequest.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                if obj.status == "approved":
                    process_registration_approval(obj)
                elif obj.status == "rejected":
                    process_registration_rejection(obj)
        super().save_model(request, obj, form, change)


admin.site.register(EventCategory)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'event_date', 'location')
    list_filter = ('category',)


# admin.site.register(Partner)
@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_user_display', 'get_total_offers', 'get_status_badge')
    search_fields = ('name', 'user__username')
    list_filter = ('name',)
    ordering = ('name',)

    # 1. Настраиваем выпадающий список пользователей
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            # Показываем только тех, кто еще не привязан к другому бизнесу
            qs = User.objects.filter(managed_partner__isnull=True)
            kwargs['queryset'] = qs
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 2. Создание/Привязка аккаунта
    def save_model(self, request, obj, form, change):
        if not change and not obj.user:
            # Если создаем нового партнера и юзер не выбран в дропдауне:
            username = f"partner_{obj.name.lower().replace(' ', '_')}_{obj.id}"
            email = f"{username}@zabgu.ru"
            raw_password = get_random_string(length=12)

            # Создаем юзера и сразу хешируем пароль
            user = User.objects.create_user(username=username, email=email, password=raw_password)

            # Добавляем в нужную группу
            try:
                partner_group = Group.objects.get(name='Партнеры')
                user.groups.add(partner_group)
            except Group.DoesNotExist:
                pass

            obj.user = user

        super().save_model(request, obj, form, change)

    def get_user_display(self, obj):
        if obj.user:
            # В строке 2 плейсхолдера {}, передаем 2 аргумента:
            # {0} - ID пользователя, {1} - Логин
            return format_html(
                '<a href="/admin/auth/user/{}/change/" target="_blank" class="text-blue-600 hover:underline font-semibold">{}</a>',
                obj.user.id,
                obj.user.username
            )
        return format_html('<span class="text-gray-400">Не привязан</span>')

    def get_total_offers(self, obj):
        count = Offer.objects.filter(partner=obj).count()
        return format_html('<span class="badge bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">{}</span>', count)

    def get_status_badge(self, obj):
        if obj.user:
            return format_html('<span class="badge bg-success text-white text-xs px-2 py-1 rounded">Активен</span>')
        return format_html(
            '<span class="badge bg-gray-200 text-gray-600 text-xs px-2 py-1 rounded">Без аккаунта</span>')

    actions = ['generate_temp_password']

    @admin.action(description='Сгенерировать новый пароль для привязанных партнеров')
    def generate_temp_password(self, request, queryset):
        count = 0
        for partner in queryset:
            if partner.user:
                new_pass = get_random_string(length=12)
                partner.user.set_password(new_pass)
                partner.user.save()
                count += 1
        if count > 0:
            self.message_user(request, f"Пароли обновлены для {count} партнеров. Проверьте консоль.", messages.SUCCESS)


# ==========================================================
# ОСТАЛЬНОЕ АДМИНКИ (опциональные улучшения)
# ==========================================================
@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'partner', 'category', 'price_in_eco', 'is_active')
    list_filter = ('partner', 'category', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('title', 'partner__name')


@admin.register(UserPromoCode)
class UserPromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'offer', 'is_used', 'created_at')
    list_filter = ('is_used', 'offer__partner')
    search_fields = ('code', 'user__username')
    readonly_fields = ('code', 'created_at')
