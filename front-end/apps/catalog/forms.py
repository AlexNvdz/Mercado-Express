from django import forms


class ProductForm(forms.Form):
    """Staff-only product create/edit form. Posts straight to backend-api
    (see services/products.py) -- there is no Django Product model.
    """

    sku = forms.CharField(label="SKU", max_length=64)
    name = forms.CharField(label="Nombre", max_length=255)
    description = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 4}))
    category_id = forms.ChoiceField(label="Categoría")
    price = forms.DecimalField(label="Precio", min_value=0, decimal_places=2, max_digits=12)
    is_active = forms.BooleanField(label="Activo (visible en el catálogo)", required=False, initial=True)

    def __init__(self, *args, categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].choices = [(c["id"], c["name"]) for c in categories or []]

    def to_api_payload(self) -> dict:
        """Shape cleaned_data to match backend-api's ProductCreate/ProductUpdate
        (see ../../API_CONTRACT.md#apiv1products) -- `price` as decimal-as-string.
        """
        data = self.cleaned_data
        return {
            "sku": data["sku"],
            "name": data["name"],
            "description": data["description"] or None,
            "category_id": data["category_id"],
            "price": str(data["price"]),
            "is_active": data["is_active"],
        }
