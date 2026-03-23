from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class RoleRequiredMixin:
    required_roles = []  # переопределите в наследнике

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if not user.groups.filter(name__in=self.required_roles).exists():
                return redirect('no-access')  # редирект по name из urls.py
                # raise PermissionDenied  # вернёт 403
        else:
            return redirect("/login/")
        return super().dispatch(request, *args, **kwargs)
