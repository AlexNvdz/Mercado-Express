from django.contrib import messages
from django.shortcuts import redirect, render

from services import auth as auth_service
from services.exceptions import ApiAuthenticationError, ApiConflictError, ApiError, ApiValidationError

from .forms import LoginForm, RegisterForm


def login_view(request):
    if auth_service.is_authenticated(request):
        return redirect("dashboard:home")

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
            messages.success(request, "Sesión iniciada correctamente.")
            next_url = request.GET.get("next") or "dashboard:home"
            return redirect(next_url)

    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if auth_service.is_authenticated(request):
        return redirect("dashboard:home")

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
        except ApiValidationError as exc:
            form.add_error(None, exc.detail)
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
