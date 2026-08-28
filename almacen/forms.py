from django import forms
from .models import Estante, Almacen


class AlmacenForm(forms.ModelForm):
    class Meta:
        model = Almacen
        fields = ['nombre', 'dimensiones', 'ubicacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'dimensiones': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EstanteForm(forms.ModelForm):
    class Meta:
        model = Estante
        fields = ['codigo_almacen', 'codigo', 'dimensiones']
        widgets = {
            'codigo_almacen': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'dimensiones': forms.TextInput(attrs={'class': 'form-control'}),
        }