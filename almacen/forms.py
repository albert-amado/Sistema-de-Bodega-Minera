from django import forms
from django.core.exceptions import ValidationError

from .models import Almacen, Estante


class AlmacenForm(forms.ModelForm):
    class Meta:
        model = Almacen
        fields = ['nombre', 'dimensiones', 'ubicacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del almacén'}),
            'dimensiones': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 20x15m'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación física en sede'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre del almacén es obligatorio.')
        if len(nombre) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')
        return nombre

    def clean_ubicacion(self):
        return (self.cleaned_data.get('ubicacion') or '').strip()

    def clean_dimensiones(self):
        return (self.cleaned_data.get('dimensiones') or '').strip()


class EstanteForm(forms.ModelForm):
    class Meta:
        model = Estante
        fields = ['codigo_almacen', 'codigo', 'dimensiones']
        widgets = {
            'codigo_almacen': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código del estante (ej: EST-01)'}),
            'dimensiones': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2x1x3m'}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip()
        if not codigo:
            raise ValidationError('El código del estante es obligatorio.')
        return codigo

    def clean_dimensiones(self):
        return (self.cleaned_data.get('dimensiones') or '').strip()