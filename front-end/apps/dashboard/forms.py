from django import forms


class AddressForm(forms.Form):
    line1 = forms.CharField(label="Dirección (línea 1)", max_length=200)
    line2 = forms.CharField(label="Dirección (línea 2)", max_length=200, required=False)
    city = forms.CharField(label="Ciudad", max_length=100)
    state = forms.CharField(label="Departamento/Estado", max_length=100)
    postal_code = forms.CharField(label="Código postal", max_length=20)
    country = forms.CharField(label="País (código ISO, ej. CO)", max_length=2)
    is_default = forms.BooleanField(label="Usar como dirección predeterminada", required=False)
