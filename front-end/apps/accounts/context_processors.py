from services import auth as auth_service


def auth(request):
    """Exposes is_api_authenticated to every template, based on the backend
    API session token -- not Django's own request.user.
    """
    return {"is_api_authenticated": auth_service.is_authenticated(request)}
