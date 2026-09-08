from functools import wraps
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse

from services import auth as auth_service


def api_login_required(view_func):
    """Like django.contrib.auth.decorators.login_required, but checks the
    backend-API session token (services.auth) instead of Django's own
    request.user, since customer identity lives in FastAPI, not Django.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not auth_service.is_authenticated(request):
            login_url = reverse("accounts:login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        return view_func(request, *args, **kwargs)

    return wrapped
