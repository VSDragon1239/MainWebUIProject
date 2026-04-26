from django.contrib import admin
from .models import ProjectType, Project, Blog, BlogImage, EcoTask, UserTaskCompletion, EcoCoinTransaction, \
    EcoHabitCategory, EcoHabit


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
