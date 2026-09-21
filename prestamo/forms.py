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
        hoy_str = timezone.localdate().isoformat()
        for name, field in self.fields.items():
            widget_type = type(field.widget)
            if issubclass(widget_type, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({"class": "form-select"})
            elif issubclass(widget_type, forms.DateInput) or name == "fecha":
                field.widget.attrs.update(
                    {"class": "form-control", "type": "date", "max": hoy_str}
                )
            elif issubclass(widget_type, forms.Textarea):
                field.widget.attrs.update({
                    "class": "form-control",
                    "rows": 2,
                    "maxlength": "500",
                    "style": "resize: vertical; max-height: 160px;"
                })
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
        fields = ["documento", "ficha", "fecha", "observaciones"]
        labels = {
            "documento": "Documento Solicitante",
            "ficha": "Ficha SENA / Programa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate().isoformat()

    def clean_documento(self):
        doc = self.cleaned_data.get("documento")
        if doc is None:
            raise ValidationError("El documento es obligatorio.")
        doc_val = getattr(doc, 'documento', None) or str(doc)
        doc_str = str(doc_val).strip()
        if not doc_str.isdigit():
            raise ValidationError("El documento debe ser numérico.")
        return doc

    def clean_fecha(self):
        fecha = self.cleaned_data.get("fecha")
        hoy = timezone.localdate()
        if fecha and fecha > hoy:
            raise ValidationError("La fecha del préstamo no puede ser una fecha futura.")
        if fecha and (hoy - fecha).days > 30:
            raise ValidationError("No se pueden registrar préstamos con más de 30 días de retroactividad.")
        return fecha


class SolicitudPrestamoUsuarioForm(HumanForm):
    class Meta:
        model = Prestamo
        fields = ["ficha", "observaciones"]
        labels = {
            "ficha": "Ficha SENA / Programa",
        }

    def clean_ficha(self):
        ficha = self.cleaned_data.get("ficha", "").strip()
        if not ficha:
            raise ValidationError("La ficha SENA es obligatoria.")
        return ficha


class DetallePrestamoForm(HumanForm):
    class Meta:
        model = DetallePrestamo
        fields = ["codigo_herramienta", "cantidad", "observaciones"]
        labels = {
            "codigo_herramienta": "Herramienta",
        }
        widgets = {"cantidad": forms.NumberInput(attrs={"min": 1, "max": 50, "step": 1})}

    def __init__(self, *args, **kwargs):
        if "data" in kwargs and kwargs["data"] is not None:
            data = kwargs["data"].copy()
            if "herramienta" in data and "codigo_herramienta" not in data:
                data["codigo_herramienta"] = data["herramienta"]
            kwargs["data"] = data
        super().__init__(*args, **kwargs)

    def clean_cantidad(self):
        cant = self.cleaned_data.get("cantidad")
        if cant is not None:
            if cant <= 0:
                raise ValidationError("La cantidad debe ser mayor a 0.")
            if cant > 50:
                raise ValidationError("La cantidad máxima por herramienta es 50 unidades.")
        return cant

    def clean(self):
        cd = super().clean()
        h = cd.get("codigo_herramienta")
        cant = cd.get("cantidad")
        if h and cant is not None:
            if cant > h.stock_disponible:
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
        fields = ["codigo_prestamo", "fecha", "observaciones"]
        labels = {"codigo_prestamo": "Préstamo a Devolver"}

    def __init__(self, *args, **kwargs):
        if "data" in kwargs and kwargs["data"] is not None:
            data = kwargs["data"].copy()
            if "prestamo" in data and "codigo_prestamo" not in data:
                data["codigo_prestamo"] = data["prestamo"]
            kwargs["data"] = data
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate().isoformat()
        self.fields["codigo_prestamo"].queryset = Prestamo.objects.exclude(
            estado=EstadoPrestamo.DEVUELTO
        )

    def clean(self):
        cd = super().clean()
        p = cd.get("codigo_prestamo")
        fecha_dev = cd.get("fecha")
        hoy = timezone.localdate()
        if fecha_dev and fecha_dev > hoy:
            self.add_error("fecha", "La fecha de devolución no puede ser futura.")
        if p and fecha_dev and p.fecha and fecha_dev < p.fecha:
            self.add_error("fecha", f"La devolución no puede ser anterior a la fecha del préstamo ({p.fecha}).")
        return cd


class EditarPrestamoObservacionesForm(HumanForm):
    class Meta:
        model = Prestamo
        fields = ["observaciones"]
