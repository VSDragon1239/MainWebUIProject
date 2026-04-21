import os
import uuid

from django.db import models
from django.contrib.auth.models import User
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit

from django.db.models import Q


def project_image_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    name = uuid.uuid4().hex
    return os.path.join('projects', 'images', f"{name}.{ext}")


def blog_image_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    name = uuid.uuid4().hex
    return os.path.join('blog', 'images', f"{name}.{ext}")


class ProjectType(models.Model):
    code = models.SlugField(unique=True, verbose_name="Код")
    name = models.CharField(max_length=100, verbose_name="Наименование")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Тип проекта"
        verbose_name_plural = "Типы проектов"

    def __str__(self):
        return self.name


class Project(models.Model):
    image = ProcessedImageField(
        upload_to=project_image_upload_to,
        processors=[ResizeToFit(128, 128)],
        format='JPEG',
        options={'quality': 85},
        blank=True,
        null=True,
        verbose_name="Изображение"
    )
    name = models.CharField("Название", max_length=200)
    type = models.ForeignKey(ProjectType, on_delete=models.SET_NULL, null=True, verbose_name="Тип проекта", )
    description = models.TextField(blank=True)
    leaders = models.ManyToManyField(User, related_name="led_projects", limit_choices_to=Q(groups__name="Руководители"),
                                     verbose_name="Руководители", )
    members = models.ManyToManyField(User, related_name="projects", limit_choices_to=Q(groups__name="Участники"),
                                     verbose_name="Участники", )
    start_date = models.DateField("Дата начала", auto_now_add=True)
    end_date = models.DateField("Дата завершения", null=True, blank=True)

    # model_files = models.FileField(upload_to="projects/models", verbose_name="Файлы модели (STL/OBJ и др.)", blank=True, null=True)

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_username()


class Blog(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(unique=True, verbose_name="slug")
    content = models.TextField(verbose_name="Содержание")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата публикации")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Автор")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title


class BlogImage(models.Model):
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = ProcessedImageField(
        upload_to=blog_image_upload_to,
        processors=[ResizeToFit(512, 512)],
        format='JPEG',
        options={'quality': 85},
        blank=True,
        null=True,
        verbose_name="Изображение"
    )
    caption = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Изображение новости"
        verbose_name_plural = "Изображения Новостей"

    def __str__(self):
        return f"Изображение для {self.blog.title}"


# --- СИСТЕМА ЭКО-КОИНОВ --- 0


# class EcoWallet(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="eco_wallet")
#     balance = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0.0000"))
#
#     class Meta:
#         verbose_name = "Кошелек эко-коинов"
#         verbose_name_plural = "Кошельки эко-коинов"
#
#     def __str__(self):
#         return f"{self.user.username}: {self.balance} ECO"


# class EcoTransactionType(models.TextChoices):
#     BLOG_CREATED = "blog_created", "Создание статьи"
#     PROJECT_CREATED = "project_created", "Создание проекта"
#     TASK_COMPLETED = "task_completed", "Выполнение эко-задачи"
#     HABIT_TRACKED = "habit_tracked", "Отметка эко-привычки"
#     SHOP_PURCHASE = "shop_purchase", "Покупка в магазине"


# class EcoCoinTransaction(models.Model):
#     wallet = models.ForeignKey(EcoWallet, on_delete=models.PROTECT, related_name="transactions")
#     amount = models.DecimalField(max_digits=20, decimal_places=4)
#     tx_type = models.CharField(max_length=30, choices=EcoTransactionType.choices)
#     external_id = models.CharField(max_length=255, blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         verbose_name = "Транзакция эко-коинов"
#         verbose_name_plural = "Транзакции эко-коинов"
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['wallet', 'tx_type', 'external_id'],
#                 condition=models.Q(external_id__isnull=False),
#                 name='unique_eco_transaction'
#             )
#         ]
class EcoWallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="eco_wallet",
        verbose_name="Владелец"
    )
    # ВАЖНО: Integer, так как это баллы, а не дубли с копейками!
    balance = models.IntegerField(
        default=0,
        verbose_name="Текущий баланс"
    )

    class Meta:
        verbose_name = "Кошелек эко-коинов"
        verbose_name_plural = "Кошельки эко-коинов"

    def __str__(self):
        return f"Кошелек: {self.user.username} ({self.balance} ECO)"


class EcoTransactionType(models.TextChoices):
    # Начисления
    PROJECT_CREATED = "project_created", "Создание проекта"
    BLOG_PUBLISHED = "blog_published", "Публикация статьи"
    DAILY_BONUS = "daily_bonus", "Ежедневный бонус"
    MANUAL_REWARD = "manual_reward", "Ручное начисление (админом)"
    # Списания
    SHOP_PURCHASE = "shop_purchase", "Покупка в магазине"
    # Переводы
    TRANSFER_OUT = "transfer_out", "Перевод другому"
    TRANSFER_IN = "transfer_in", "Перевод от другого"
    TASK_COMPLETED = "task_completed", "Выполнение эко-задачи"


class EcoCoinTransaction(models.Model):
    """
    Журнал операций (Ledger). Никогда не изменяйте записи в этой таблице (только CREATE).
    """
    wallet = models.ForeignKey(
        EcoWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Кошелек"
    )
    amount = models.IntegerField(
        verbose_name="Сумма (целое число)"
    )
    tx_type = models.CharField(
        max_length=30,
        choices=EcoTransactionType.choices,
        verbose_name="Тип операции"
    )
    # Идемпотентность: позволяет не дать баллы дважды за одно действие
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID связанной сущности",
        help_text="Например: 'blog:15' или 'project:42'"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Транзакция эко-коинов"
        verbose_name_plural = "Транзакции эко-коинов"
        # Защита от дублей на уровне БД
        constraints = [
            models.UniqueConstraint(
                fields=['wallet', 'tx_type', 'external_id'],
                condition=models.Q(external_id__isnull=False),
                name='unique_eco_transaction_for_entity'
            )
        ]

    def __str__(self):
        sign = "+" if self.amount > 0 else ""
        return f"{self.wallet.user.username}: {sign}{self.amount} ({self.get_tx_type_display()})"


class EcoTask(models.Model):
    """Задание, которое создает Админ"""
    title = models.CharField(max_length=255, verbose_name="Название задания")
    description = models.TextField(blank=True, verbose_name="Описание")
    reward = models.IntegerField(
        default=10,
        verbose_name="Награда (ECO)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Эко-задание"
        verbose_name_plural = "Эко-задания"

    def __str__(self):
        return f"{self.title} (+{self.reward} ECO)"


class UserTaskCompletion(models.Model):
    """
    Связующая таблица. Нужна для двух вещей:
    1. Чтобы в UI скрывать уже выполненные задания.
    2. Двойной контроль (наряду с external_id в транзакциях).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="completed_tasks")
    task = models.ForeignKey(EcoTask, on_delete=models.PROTECT, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Выполненное задание"
        verbose_name_plural = "Выполненные задания"
        # Пользователь может выполнить конкретное задание только ОДИН раз
        unique_together = ['user', 'task']

    def __str__(self):
        return f"{self.user.username} выполнил '{self.task.title}'"
