from django.contrib import messages
from django.shortcuts import redirect, render

from services import auth as auth_service
from services.exceptions import ApiAuthenticationError, ApiConflictError, ApiError, ApiValidationError

from .forms import LoginForm, RegisterForm


def login_view(request):
    if auth_service.is_authenticated(request):
        return redirect("adminpanel:home" if auth_service.is_staff(request) else "dashboard:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            tokens = auth_service.login(form.cleaned_data["email"], form.cleaned_data["password"])
        except ApiAuthenticationError:
            form.add_error(None, "Correo o contraseña incorrectos.")
        except ApiError:
            form.add_error(None, "No fue posible conectar con el servicio. Intenta más tarde.")
        else:
            auth_service.save_tokens(
                request,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
            )
            user = auth_service.get_current_user(tokens["access_token"])
            if user:
                auth_service.save_role(request, user["role"])
            messages.success(request, "Sesión iniciada correctamente.")
            default_next = "adminpanel:home" if auth_service.is_staff(request) else "dashboard:home"
            next_url = request.GET.get("next") or default_next
            return redirect(next_url)

    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if auth_service.is_authenticated(request):
        return redirect("adminpanel:home" if auth_service.is_staff(request) else "dashboard:home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            auth_service.register(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"] or None,
            )
        except ApiConflictError:
            form.add_error("email", "Ya existe una cuenta con este correo.")
        except ApiValidationError:
            form.add_error(None, "Revisa los datos del formulario.")
        except ApiError:
            form.add_error(None, "No fue posible crear la cuenta. Intenta más tarde.")
        else:
            messages.success(request, "Cuenta creada. Ahora puedes iniciar sesión.")
            return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
    auth_service.clear_tokens(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("core:home")
