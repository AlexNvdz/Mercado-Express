from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import api_staff_required
from services import auth as auth_service
from services import inventory, products
from services.exceptions import ApiConflictError, ApiError, ApiValidationError

from .forms import ProductForm


def product_list(request, category_id=None):
    search = request.GET.get("q", "").strip()
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1

    result = products.list_products(
        category_id=str(category_id) if category_id else None,
        search=search or None,
        page=page,
    )
    categories = products.list_categories()["items"]
    active_category = next((c for c in categories if c["id"] == str(category_id)), None)

    context = {
        "products": result["items"],
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "has_previous": result["page"] > 1,
        "has_next": result["page"] < result["pages"],
        "categories": categories,
        "active_category": active_category,
        "search": search,
    }
    return render(request, "catalog/list.html", context)


def product_detail(request, product_id):
    product = products.get_product(str(product_id))
    if product is None:
        raise Http404("Producto no encontrado")

    category = products.get_category(product["category_id"])
    availability = inventory.get_availability(product["id"])

    context = {"product": product, "category": category, "availability": availability}
    return render(request, "catalog/detail.html", context)


@require_POST
def wishlist_toggle(request, product_id):
    product = products.get_product(str(product_id))
    if product is None:
        messages.error(request, "Producto no encontrado.")
        return redirect("core:home")

    favorited = request.wishlist.toggle(str(product_id))
    if favorited:
        messages.success(request, f"{product['name']} añadido a favoritos.")
    else:
        messages.info(request, f"{product['name']} quitado de favoritos.")
    return redirect(request.POST.get("next") or "catalog:wishlist")


def wishlist_view(request):
    return render(request, "catalog/wishlist.html", {"products": list(request.wishlist)})


# --- Staff-only product management -----------------------------------------
# See API_CONTRACT.md#apiv1products. No Django Product model -- these views
# call services/products.py, which calls backend-api directly.


@api_staff_required
def product_admin_list(request):
    result = products.list_products(page=1, page_size=100)
    return render(request, "catalog/admin_list.html", {"products": result["items"], "active_nav": "products"})


@api_staff_required
def product_admin_create(request):
    token = auth_service.get_access_token(request)
    categories = products.list_categories(page_size=100)["items"]
    form = ProductForm(request.POST or None, categories=categories)

    if request.method == "POST" and form.is_valid():
        try:
            product = products.create_product(token, form.to_api_payload())
        except ApiConflictError:
            form.add_error("sku", "Ya existe un producto con ese SKU.")
        except ApiValidationError:
            form.add_error(None, "Revisa los datos del producto.")
        except ApiError:
            form.add_error(None, "No fue posible crear el producto. Intenta más tarde.")
        else:
            messages.success(request, "Producto creado. Ahora puedes subirle imágenes.")
            return redirect("catalog:admin_edit", product_id=product["id"])

    return render(request, "catalog/admin_form.html", {"form": form, "product": None, "active_nav": "products"})


@api_staff_required
def product_admin_edit(request, product_id):
    product = products.get_product(str(product_id))
    if product is None:
        raise Http404("Producto no encontrado")

    categories = products.list_categories(page_size=100)["items"]
    token = auth_service.get_access_token(request)

    if request.method == "POST":
        form = ProductForm(request.POST, categories=categories)
        if form.is_valid():
            try:
                products.update_product(token, str(product_id), form.to_api_payload())
            except ApiConflictError:
                form.add_error("sku", "Ya existe un producto con ese SKU.")
            except ApiValidationError:
                form.add_error(None, "Revisa los datos del producto.")
            except ApiError:
                form.add_error(None, "No fue posible actualizar el producto. Intenta más tarde.")
            else:
                messages.success(request, "Producto actualizado.")
                return redirect("catalog:admin_edit", product_id=product_id)
    else:
        form = ProductForm(
            initial={
                "sku": product["sku"],
                "name": product["name"],
                "description": product.get("description"),
                "category_id": product["category_id"],
                "price": product["price"],
                "is_active": product["is_active"],
            },
            categories=categories,
        )

    return render(
        request, "catalog/admin_form.html", {"form": form, "product": product, "active_nav": "products"}
    )


@api_staff_required
@require_POST
def product_admin_delete(request, product_id):
    token = auth_service.get_access_token(request)
    try:
        products.delete_product(token, str(product_id))
    except ApiError:
        messages.error(request, "No fue posible eliminar el producto.")
    else:
        messages.success(request, "Producto y sus imágenes eliminados.")
    return redirect("catalog:admin_list")


@api_staff_required
@require_POST
def product_admin_upload_image(request, product_id):
    token = auth_service.get_access_token(request)
    file = request.FILES.get("file")
    if not file:
        messages.error(request, "Selecciona una imagen.")
    else:
        try:
            products.upload_product_image(
                token,
                str(product_id),
                filename=file.name,
                content=file.read(),
                content_type=file.content_type or "application/octet-stream",
            )
        except ApiValidationError:
            messages.error(request, "Imagen no válida: usa jpg/png/webp, máximo 5MB.")
        except ApiError:
            messages.error(request, "No fue posible subir la imagen. Intenta más tarde.")
        else:
            messages.success(request, "Imagen subida.")
    return redirect("catalog:admin_edit", product_id=product_id)


@api_staff_required
@require_POST
def product_admin_delete_image(request, product_id, image_id):
    token = auth_service.get_access_token(request)
    try:
        products.delete_product_image(token, str(product_id), str(image_id))
    except ApiError:
        messages.error(request, "No fue posible eliminar la imagen.")
    else:
        messages.success(request, "Imagen eliminada.")
    return redirect("catalog:admin_edit", product_id=product_id)
