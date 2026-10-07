from services import auth as auth_service


def auth(request):
    """Exposes is_api_authenticated / is_api_staff to every template, based
    on the backend API session token/role -- not Django's own request.user.
    """
    return {
        "is_api_authenticated": auth_service.is_authenticated(request),
        "is_api_staff": auth_service.is_staff(request),
    }
