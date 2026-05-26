import csv

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.core.validators import RegexValidator
from django.template.defaultfilters import slugify
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from WebUiProject.models import Blog, BlogImage, Project, ProjectType, Profile, Offer

from django.forms.models import inlineformset_factory
from django_select2.forms import Select2Widget


# Функция для загрузки CSV (вынесите в утилиты, если используется часто)
def load_groups_from_csv(file_path='WebUIProjectGreenZabGU/zabgu_groups/all_groups_abc.csv'):
    groups = []
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)  # Пропускаем заголовок "Группа"
            groups = [row[0].strip() for row in reader if row]
    except FileNotFoundError:
        pass  # Вернет пустой список, если файла нет
    return groups


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


class RegistrationRequestForm(forms.Form):
    # Валидатор для номера телефона (формат: +79991112233)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+79991112233'. До 15 цифр."
    )

    fio = forms.CharField(
        max_length=150,
        label="ФИО",
        widget=forms.TextInput(
            attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                   'placeholder': 'Иванов Иван Иванович'})
    )
    GROUP_CHOICES = [("", "Начните вводить название группы...")] + \
                    [(group, group) for group in load_groups_from_csv()]

    group = forms.ChoiceField(
        label="Группа",
        choices=GROUP_CHOICES,
        widget=Select2Widget(
            attrs={
                # Ваши Tailwind классы применятся к обертке Select2
                'class': 'w-full',
                'data-placeholder': 'ИЭ-21-1',
                'data-minimum-input-length': 1,  # Искать после ввода первой буквы
                'style': 'min-height: 42px;'  # Чтобы высота совпадала с другими полями
            }
        )
    )
    phone = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        label="Номер телефона",
        widget=forms.TextInput(
            attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                   'placeholder': '+79991112233'})
    )
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(
            attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                   'placeholder': 'example@mail.ru'})
    )

    # Добавляем капчу
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                # Если нужно изменить размер на компактный, раскомментируйте:
                # 'data-size': 'compact'
            }
        )
    )
    # Поле согласия, обязательное для галочки (required=True по умолчанию)
    agreement = forms.BooleanField(
        label="Я даю согласие на обработку персональных данных",
        widget=forms.CheckboxInput(
            attrs={'class': 'w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500'})
    )


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


# class ProfileAvatarForm(forms.ModelForm):
#     class Meta:
#         model = Profile
#         fields = ['avatar']
class ProfileAvatarForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500',
            'rows': 4}),
        required=False
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'description', 'phone']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'hidden', 'id': 'avatar_input'}),
            # Скрытый input, нажатие на кастомную кнопку вызовет его
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
        }


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
        }


class OfferCreateForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['title', 'description', 'price_in_eco', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500',
                'rows': 3}),
            'price_in_eco': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
        }


class PartnerUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'vTextField', 'autocomplete': 'new-password'}),
        label="Пароль"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']  # Только нужные поля

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 8:
            raise forms.ValidationError("Пароль должен быть не менее 8 символов.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["password"]
        user.set_password(password)
        if commit:
            user.save()
        return user
