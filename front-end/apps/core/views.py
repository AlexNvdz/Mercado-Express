from django.shortcuts import render

from services import products


def home(request):
    categories = products.list_categories()["items"]
    featured_products = products.list_products()["items"][:8]
    context = {
        "categories": categories,
        "featured_products": featured_products,
    }
    return render(request, "core/home.html", context)
