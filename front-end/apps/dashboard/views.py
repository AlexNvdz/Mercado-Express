from django.contrib import messages
from django.shortcuts import redirect, render

from apps.accounts.decorators import api_login_required
from services import auth as auth_service
from services import customers as customers_service
from services.exceptions import ApiError

from .forms import AddressForm, ProfileForm


@api_login_required
def profile(request):
    token = auth_service.get_access_token(request)
    user = customers_service.get_profile(token)

    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            try:
                user = customers_service.update_profile(
                    token,
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"] or None,
                )
            except ApiError:
                messages.error(request, "No fue posible actualizar tu perfil.")
            else:
                messages.success(request, "Perfil actualizado.")
                return redirect("dashboard:profile")
    else:
        form = ProfileForm(
            initial={"full_name": user.get("full_name") if user else "", "phone": user.get("phone") if user else ""}
        )

    return render(request, "dashboard/profile.html", {"user": user, "form": form})


@api_login_required
def address_list(request):
    token = auth_service.get_access_token(request)
    addresses = customers_service.list_addresses(token)
    return render(request, "dashboard/addresses.html", {"addresses": addresses})


@api_login_required
def address_add(request):
    token = auth_service.get_access_token(request)
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            customers_service.add_address(token, form.cleaned_data)
        except ApiError:
            form.add_error(None, "No fue posible guardar la dirección. Intenta más tarde.")
        else:
            messages.success(request, "Dirección guardada.")
            next_url = request.POST.get("next") or "dashboard:addresses"
            return redirect(next_url)

    return render(request, "dashboard/address_form.html", {"form": form})


@api_login_required
def address_delete(request, address_id):
    if request.method == "POST":
        token = auth_service.get_access_token(request)
        customers_service.delete_address(token, str(address_id))
        messages.success(request, "Dirección eliminada.")
    return redirect("dashboard:addresses")


@api_login_required
def address_set_default(request, address_id):
    if request.method == "POST":
        token = auth_service.get_access_token(request)
        try:
            customers_service.update_address(token, str(address_id), {"is_default": True})
        except ApiError:
            messages.error(request, "No fue posible actualizar la dirección.")
        else:
            messages.success(request, "Dirección predeterminada actualizada.")
    return redirect("dashboard:addresses")
