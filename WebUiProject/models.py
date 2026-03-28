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
    type = models.ForeignKey(ProjectType, on_delete=models.SET_NULL, null=True, verbose_name="Тип проекта",)
    description = models.TextField(blank=True)
    leaders = models.ManyToManyField(User, related_name="led_projects", limit_choices_to=Q(groups__name="Руководители"), verbose_name="Руководители",)
    members = models.ManyToManyField(User, related_name="projects", limit_choices_to=Q(groups__name="Участники"), verbose_name="Участники",)
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
