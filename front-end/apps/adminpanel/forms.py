from django import forms

from services.orders import ORDER_STATUSES


class CategoryForm(forms.Form):
    """Staff-only category create/edit form. Posts straight to backend-api
    (see services/products.py:create_category/update_category).
    """

    name = forms.CharField(label="Nombre", max_length=120)
    description = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    parent_id = forms.ChoiceField(label="Categoría padre", required=False)
    is_active = forms.BooleanField(label="Activa (visible en el catálogo)", required=False, initial=True)

    def __init__(self, *args, categories=None, exclude_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "— Ninguna (categoría principal) —")]
        choices += [(c["id"], c["name"]) for c in categories or [] if c["id"] != exclude_id]
        self.fields["parent_id"].choices = choices

    def to_api_payload(self) -> dict:
        data = self.cleaned_data
        return {
            "name": data["name"],
            "description": data["description"] or None,
            "parent_id": data["parent_id"] or None,
            "is_active": data["is_active"],
        }


class InventoryAdjustForm(forms.Form):
    """Quick stock movement: positive delta restocks, negative removes
    (shrinkage/correction). See services/inventory.py:adjust_stock.
    """

    delta = forms.IntegerField(label="Cantidad (+/-)", widget=forms.NumberInput(attrs={"placeholder": "+10 / -5"}))
    reason = forms.CharField(label="Motivo", required=False, max_length=255)


class ReorderLevelForm(forms.Form):
    """Sets the low-stock alert threshold for one product."""

    reorder_level = forms.IntegerField(label="Nivel de reorden", min_value=0)


class OrderStatusForm(forms.Form):
    """Force a status transition directly. See services/orders.py:update_status.
    Prefer /payments and /shipments for the normal flow -- this is for
    manual corrections.
    """

    status = forms.ChoiceField(label="Nuevo estado", choices=[(s, s) for s in ORDER_STATUSES])


class ShipmentCreateForm(forms.Form):
    """Starts a shipment for a paid order. address_id comes from the order
    itself (shipping_address_id, set at checkout) -- staff only picks the
    carrier.
    """

    carrier = forms.CharField(label="Transportadora", required=False, max_length=100)
