"""
forms.py - Formularios con listas blancas explícitas para actualización de configuración.
"""
from django import forms
from .schemas import DatabaseDriver, DatabaseTarget, StorageDriver, LogLevel


class ConmutadorDBForm(forms.Form):
    target = forms.ChoiceField(
        choices=[(t.value, t.name.capitalize()) for t in DatabaseTarget],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    test_first = forms.BooleanField(required=False, initial=True)


class PerfilDatabaseForm(forms.Form):
    driver = forms.ChoiceField(
        choices=[(d.value, d.name.capitalize()) for d in DatabaseDriver],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    host = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    port = forms.IntegerField(min_value=1, max_value=65535, widget=forms.NumberInput(attrs={"class": "form-control"}))
    name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    user = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(max_length=255, required=False, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Dejar en blanco para mantener actual"}))
    ssl_mode = forms.ChoiceField(
        choices=[("disable", "Disable"), ("prefer", "Prefer"), ("require", "Require"), ("verify-full", "Verify Full")],
        widget=forms.Select(attrs={"class": "form-select"})
    )


class ParametrosSistemaForm(forms.Form):
    debug = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
    log_level = forms.ChoiceField(choices=[(l.value, l.value) for l in LogLevel], widget=forms.Select(attrs={"class": "form-select"}))
    timezone = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control"}))
    language_code = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "form-control"}))
    currency_symbol = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "form-control"}))
    storage_driver = forms.ChoiceField(choices=[(s.value, s.name) for s in StorageDriver], widget=forms.Select(attrs={"class": "form-select"}))
