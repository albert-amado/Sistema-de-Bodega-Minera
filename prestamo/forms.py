from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import timezone

from herramienta.models import Herramienta

from .models import (
    DetallePrestamo,
    DevolucionHerramienta,
    EstadoPrestamo,
    Prestamo,
)


class HumanForm(forms.ModelForm):
    """Clase base para aplicar estilos CSS y comportamientos amigables."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget_type = type(field.widget)
            if issubclass(widget_type, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({"class": "form-select"})
            elif issubclass(widget_type, forms.DateInput) or name == "fecha":
                field.widget.attrs.update(
                    {"class": "form-control", "type": "date"}
                )
            elif issubclass(widget_type, forms.Textarea):
                field.widget.attrs.update({"class": "form-control", "rows": 2})
            else:
                field.widget.attrs.update(
                    {"class": "form-control", "autocomplete": "off"}
                )


class HerramientaForm(HumanForm):
    class Meta:
        model = Herramienta
        fields = [
            "codigo_sku",
            "nombre_herramienta",
            "descripcion",
            "disponibilidad",
        ]
        labels = {
            "codigo_sku": "Código / SKU",
            "nombre_herramienta": "Nombre",
            "disponibilidad": "Stock / Disponibilidad",
        }


class PrestamoForm(HumanForm):
    class Meta:
        model = Prestamo
        fields = ["documento", "ficha", "fecha", "estado", "observaciones"]
        labels = {
            "documento": "Documento Solicitante",
            "ficha": "Ficha SENA / Programa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.now().strftime("%Y-%m-%d")

    def clean_documento(self):
        doc = self.cleaned_data.get("documento", "").strip()
        if not doc.isdigit():
            raise ValidationError("El documento debe ser numérico.")
        return doc


class DetallePrestamoForm(HumanForm):
    class Meta:
        model = DetallePrestamo
        fields = ["herramienta", "cantidad", "observaciones"]
        widgets = {"cantidad": forms.NumberInput(attrs={"min": 1})}

    def clean(self):
        cd = super().clean()
        h, cant = cd.get("herramienta"), cd.get("cantidad")
        if h and cant and cant > h.stock_disponible:
            msg = (
                f"Stock insuficiente. Solo hay {h.stock_disponible} "
                "disponibles."
            )
            self.add_error("cantidad", msg)
        return cd


DetallePrestamoFormSet = inlineformset_factory(
    Prestamo,
    DetallePrestamo,
    form=DetallePrestamoForm,
    extra=1,
    can_delete=True,
)


class DevolucionHerramientaForm(HumanForm):
    class Meta:
        model = DevolucionHerramienta
        fields = ["prestamo", "codigo_recibe", "fecha", "observaciones"]
        labels = {"codigo_recibe": "Documento de Quien Recibe"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.now().strftime("%Y-%m-%d")
        self.fields["prestamo"].queryset = Prestamo.objects.exclude(
            estado=EstadoPrestamo.DEVUELTO
        )
