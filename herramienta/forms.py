import re
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Herramienta,
    CategoriaHerramienta,
    Proveedor,
    Traslado,
    DetalleTraslado,
    Mantenimiento,
    DetalleMantenimiento,
    BitacoraEstado,
)


class HerramientaForm(forms.ModelForm):
    class Meta:
        model = Herramienta
        fields = [
            'codigo_sku',
            'nombre_herramienta',
            'descripcion',
            'disponibilidad',
            'codigo_categoria',
            'estante',
        ]
        widgets = {
            'codigo_sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SKU-001'}),
            'nombre_herramienta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del equipo o herramienta'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción detallada'}),
            'disponibilidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad disponible o Disponible'}),
            'codigo_categoria': forms.Select(attrs={'class': 'form-select'}),
            'estante': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nombre_herramienta(self):
        nombre = self.cleaned_data.get('nombre_herramienta', '').strip()
        if not nombre:
            raise ValidationError('El nombre de la herramienta es obligatorio.')
        return nombre

    def clean_disponibilidad(self):
        disp = self.cleaned_data.get('disponibilidad', '').strip()
        if not disp:
            return 'Disponible'
        if disp.isdigit():
            val = int(disp)
            if val < 0:
                raise ValidationError('La disponibilidad no puede ser un número negativo.')
            return str(val)
        return disp


class CategoriaHerramientaForm(forms.ModelForm):
    class Meta:
        model = CategoriaHerramienta
        fields = [
            'nombre_categoria',
            'tipo_herramienta',
            'descripcion',
        ]
        widgets = {
            'nombre_categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'tipo_herramienta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tipo (ej. Manual, Eléctrica, Minería)'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción'}),
        }

    def clean_nombre_categoria(self):
        nombre = self.cleaned_data.get('nombre_categoria', '').strip()
        if not nombre:
            raise ValidationError('El nombre de la categoría es obligatorio.')
        return nombre


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            'nit_proveedor',
            'telefono_contacto',
            'correo_proveedor',
            'descripcion',
        ]
        widgets = {
            'nit_proveedor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT o Identificación'}),
            'telefono_contacto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'correo_proveedor': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@proveedor.com'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción / Observaciones'}),
        }

    def clean_nit_proveedor(self):
        nit = self.cleaned_data.get('nit_proveedor', '').strip()
        if not nit:
            raise ValidationError('El NIT del proveedor es obligatorio.')
        return nit

    def clean_telefono_contacto(self):
        tel = self.cleaned_data.get('telefono_contacto', '').strip()
        if tel and not re.match(r'^[0-9+\-\s()]+$', tel):
            raise ValidationError('El teléfono contiene caracteres inválidos.')
        return tel


class TrasladoForm(forms.ModelForm):
    class Meta:
        model = Traslado
        fields = [
            'fecha_movimiento',
            'dimensiones',
            'tipo_movimiento',
            'num_estante_origen',
            'observaciones',
        ]
        widgets = {
            'fecha_movimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dimensiones': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_movimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'num_estante_origen': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DetalleTrasladoForm(forms.ModelForm):
    class Meta:
        model = DetalleTraslado
        fields = [
            'codigo_traslado',
            'codigo_herramienta',
            'cantidad',
            'observaciones',
        ]
        widgets = {
            'codigo_traslado': forms.Select(attrs={'class': 'form-select'}),
            'codigo_herramienta': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_cantidad(self):
        cant = self.cleaned_data.get('cantidad')
        if cant is not None and cant <= 0:
            raise ValidationError('La cantidad trasladada debe ser mayor a 0.')
        return cant
