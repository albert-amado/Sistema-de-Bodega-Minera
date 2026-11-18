import re

from django.core.exceptions import ValidationError


class ReglasContrasenaValidator:
    """
    Exige: mínimo de caracteres, mayúsculas, minúsculas y números.
    Es la misma política que valida usuario.js en el navegador.
    """

    def __init__(self, min_length=10, min_upper=1, min_lower=1, min_digits=2):
        self.min_length = min_length
        self.min_upper = min_upper
        self.min_lower = min_lower
        self.min_digits = min_digits

    def validate(self, password, user=None):
        errores = []
        if len(password) < self.min_length:
            errores.append(f'mínimo {self.min_length} caracteres')
        if len(re.findall(r'[A-ZÁÉÍÓÚÑ]', password)) < self.min_upper:
            errores.append('una mayúscula')
        if len(re.findall(r'[a-záéíóúñ]', password)) < self.min_lower:
            errores.append('una minúscula')
        if len(re.findall(r'\d', password)) < self.min_digits:
            errores.append(f'al menos {self.min_digits} números')
        if errores:
            raise ValidationError(
                'La contraseña debe tener ' + ', '.join(errores) + '.',
                code='password_reglas',
            )

    def get_help_text(self):
        return (
            f'Mínimo {self.min_length} caracteres, {self.min_upper} mayúscula, '
            f'{self.min_lower} minúscula y {self.min_digits} números.'
        )