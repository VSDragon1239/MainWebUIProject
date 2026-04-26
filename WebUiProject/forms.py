from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.template.defaultfilters import slugify

from .models import Blog, BlogImage, Project, ProjectType, Profile

from django.forms.models import inlineformset_factory


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Имя пользователя', max_length=150)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class CustomUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content']


class BlogPostImageForm(forms.ModelForm):
    class Meta:
        model = BlogImage
        fields = ['image']


# создаём formset для картинок
BlogPostImageFormSet = inlineformset_factory(
    Blog,
    BlogImage,
    form=BlogPostImageForm,
    extra=3,  # количество пустых форм "по умолчанию"
    can_delete=True
)

ROLE_CHOICES = (
    ("Участники", "Участник"),
    ("Руководители", "Руководитель"),
    ("Контент-менеджеры", "Контент-менеджер"),
)


class UserCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Роль")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Добавляем пользователя в выбранную группу
            role_name = self.cleaned_data["role"]
            group = Group.objects.get(name=role_name)
            user.groups.add(group)
        return user


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "image", "name", "type", "description",
            "leaders", "members", "end_date"
        ]
        labels = {
            "image": "Изображение",
            "name": "Название",
            "type": "Тип проекта",
            "description": "Описание",
            "leaders": "Руководители",
            "members": "Участники",
            "end_date": "Дата завершения",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Красивый пустой пункт у типа
        if "type" in self.fields:
            self.fields["type"].empty_label = "— выберите тип —"

        # Лидеры: только «Руководители»
        try:
            g_leads = Group.objects.get(name="Руководители")
            self.fields["leaders"].queryset = (
                User.objects.filter(groups=g_leads, is_active=True)
                .order_by("last_name", "first_name", "username")
            )
        except Group.DoesNotExist:
            self.fields["leaders"].queryset = User.objects.none()
            self.fields["leaders"].help_text = "Создайте группу «Руководители»."

        # Участники: по желанию — только «Участники»
        try:
            g_members = Group.objects.get(name="Участники")
            self.fields["members"].queryset = (
                User.objects.filter(groups=g_members, is_active=True)
                .order_by("last_name", "first_name", "username")
            )
        except Group.DoesNotExist:
            self.fields["members"].queryset = User.objects.filter(is_active=True)

        # Единый класс для полей
        for f in self.fields.values():
            if not isinstance(f.widget, (forms.CheckboxInput, forms.RadioSelect)):
                f.widget.attrs.setdefault("class", "form-input")

    def clean_leaders(self):
        leaders = self.cleaned_data.get("leaders")
        invalid = leaders.exclude(groups__name="Руководители")
        if invalid.exists():
            bad = ", ".join(invalid.values_list("username", flat=True))
            raise forms.ValidationError(
                f"Эти пользователи не в группе «Руководители»: {bad}"
            )
        return leaders


class ProjectTypeForm(forms.ModelForm):
    class Meta:
        model = ProjectType
        fields = ["name", "code", "description"]
        labels = {
            "name": "Наименование",
            "code": "Код (slug)",
            "description": "Описание",
        }

    def clean_code(self):
        code = self.cleaned_data.get("code") or ""
        if not code:
            # генерим из name
            code = slugify(self.cleaned_data.get("name", ""))
        if not code:
            raise forms.ValidationError("Код не может быть пустым.")
        self.cleaned_data["code"] = code
        return code


class UserUpdateForm(UserChangeForm):
    password = None  # скрываем стандартное поле пароля
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Роль")

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "role"
        ]


class ProfileAvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']
