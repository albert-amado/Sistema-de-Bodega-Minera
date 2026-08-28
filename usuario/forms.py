from django import forms
from .models import Usuario


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            'documento',
            'primer_nombre',
            'segundo_nombre',
            'primer_apellido',
            'segundo_apellido',
            'correo_personal',
            'telefono',
            'tipo_documento',
            'programa',
            'ficha',
        ]
        widgets = {
            'documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1234567890'}),
            'primer_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer nombre'}),
            'segundo_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Segundo nombre (opcional)'}),
            'primer_apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer apellido'}),
            'segundo_apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Segundo apellido (opcional)'}),
            'correo_personal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 3001234567'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'programa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Programa de formación'}),
            'ficha': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de ficha'}),
        }