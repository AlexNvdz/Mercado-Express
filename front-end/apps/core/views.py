from django.shortcuts import redirect, render

from services import auth as auth_service
from services import products


def home(request):
    # Admin/employee accounts manage the store from the dashboard, not the
    # storefront -- see apps/adminpanel.
    if auth_service.is_staff(request):
        return redirect("adminpanel:home")

    categories = products.list_categories()["items"]
    featured_products = products.list_products()["items"][:8]
    context = {
        "categories": categories,
        "featured_products": featured_products,
    }
    return render(request, "core/home.html", context)
