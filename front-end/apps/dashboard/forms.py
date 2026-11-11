from django import forms


class ProfileForm(forms.Form):
    full_name = forms.CharField(label="Nombre completo", max_length=150)
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)


class AddressForm(forms.Form):
    """Colombian addresses only (the store ships with Envia.com inside
    Colombia). The department comes from the backend's list and the city
    field suggests that department's cities (static/js/modules/address-form.js);
    the backend checks the city and fills in the postal code."""

    line1 = forms.CharField(
        label="Dirección",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Calle 10 # 5-20", "autocomplete": "address-line1"}),
    )
    line2 = forms.CharField(
        label="Apartamento, torre o barrio (opcional)",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "address-line2"}),
    )
    state = forms.ChoiceField(label="Departamento")
    city = forms.CharField(
        label="Ciudad o municipio",
        max_length=100,
        widget=forms.TextInput(attrs={"list": "city-options", "autocomplete": "off"}),
    )
    phone = forms.CharField(
        label="Teléfono de quien recibe",
        max_length=30,
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )
    is_default = forms.BooleanField(label="Usar como dirección predeterminada", required=False)

    def __init__(self, *args, states: list[dict], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["state"].choices = [("", "Elige un departamento")] + [
            (state["name"], state["name"]) for state in states
        ]

    def to_api(self) -> dict:
        return {**self.cleaned_data, "country": "CO"}
