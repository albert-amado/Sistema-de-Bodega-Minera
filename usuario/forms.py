import re

from django import forms
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError

from .models import Usuario

DOC_PATTERNS = {
    'CC': (r'^\d{6,10}$', 'La Cédula de Ciudadanía debe contener entre 6 y 10 dígitos numéricos.'),
    'CE': (r'^[A-Za-z0-9]{6,12}$', 'La Cédula de Extranjería debe contener entre 6 y 12 caracteres alfanuméricos.'),
    'PP': (r'^[A-Za-z0-9]{5,9}$', 'El Pasaporte debe contener entre 5 y 9 caracteres alfanuméricos.'),
    'TI': (r'^\d{10,11}$', 'La Tarjeta de Identidad debe contener 10 u 11 dígitos numéricos.'),
}


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
            'correo_personal': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 3001234567'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'programa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Programa de formación'}),
            'ficha': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de ficha'}),
        }

    def clean_documento(self):
        doc = self.cleaned_data.get('documento', '').strip()
        tipo = self.cleaned_data.get('tipo_documento') or self.data.get('tipo_documento', 'CC')
        if not doc:
            raise ValidationError('El número de documento es obligatorio.')
        patron, mensaje = DOC_PATTERNS.get(tipo, (None, None))
        if patron and not re.match(patron, doc):
            raise ValidationError(mensaje)
        return doc

    def clean_correo_personal(self):
        correo = self.cleaned_data.get('correo_personal', '').strip().lower()
        if correo:
            qs = Usuario.objects.filter(correo_personal=correo)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Este correo ya se encuentra registrado.')
        return correo

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '').strip()
        if tel and not tel.isdigit():
            raise ValidationError('El teléfono solo debe contener números.')
        return tel


class RegistroUsuarioForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        choices=Usuario.TIPO_DOCUMENTO_CHOICES,
        initial='CC',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    documento = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de documento'})
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer nombre'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer apellido'})
    )
    email = forms.EmailField(
        max_length=100,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres'})
    )
    password2 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite tu contraseña'})
    )
    numero_ficha = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de ficha'})
    )
    nombre_programa = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Programa de formación'})
    )

    def clean_documento(self):
        doc = self.cleaned_data.get('documento', '').strip()
        tipo = self.cleaned_data.get('tipo_documento', 'CC')
        patron, mensaje = DOC_PATTERNS.get(tipo, (None, None))
        if patron and not re.match(patron, doc):
            raise ValidationError(mensaje)
        if Usuario.objects.filter(documento=doc).exists():
            raise ValidationError('Ya existe un usuario con ese número de documento.')
        return doc

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if Usuario.objects.filter(correo_personal=email).exists():
            raise ValidationError('El correo ya está registrado.')
        return email

    def clean(self):
        cd = super().clean()
        p1 = cd.get('password1')
        p2 = cd.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')

        doc = cd.get('documento')
        tipo = cd.get('tipo_documento', 'CC')

        if doc and not self.errors.get('documento'):
            # Consulta aislada contra el servicio SofiaPlus (reutilización sin duplicar lógica)
            from django.conf import settings
            from django.utils import timezone
            from services.sofia_plus_client import (
                get_sofia_plus_client,
                AprendizNotFoundError,
                SofiaPlusServiceUnavailableError,
                SofiaPlusInvalidInputError,
                SofiaPlusError,
            )

            client = get_sofia_plus_client()
            try:
                aprendiz = client.consultar_aprendiz(tipo, doc)
                # Aprendiz encontrado y verificado exitosamente
                self._verificado_sofia_plus = True
                self._fecha_verificacion = timezone.now()

                # Asegurar nombres y datos académicos oficiales desde SofiaPlus (no editables manualmente)
                cd['first_name'] = aprendiz.primer_nombre
                cd['last_name'] = aprendiz.primer_apellido
                cd['numero_ficha'] = aprendiz.numero_ficha
                cd['nombre_programa'] = aprendiz.programa_formacion
                self._aprendiz_info = aprendiz

            except AprendizNotFoundError as exc:
                # TODO: [DECISIÓN DE NEGOCIO PENDIENTE] ALLOW_MANUAL_REGISTRATION
                # Define si permitimos registrar manualmente aprendices que no figuren en SofiaPlus
                allow_manual = getattr(settings, 'ALLOW_MANUAL_REGISTRATION', False)
                if allow_manual:
                    self._verificado_sofia_plus = False
                    self._fecha_verificacion = None
                else:
                    self.add_error(
                        'documento',
                        'El documento no se encuentra registrado en SofiaPlus. '
                        'Solo aprendices verificados del SENA pueden crear una cuenta en el sistema.'
                    )

            except SofiaPlusServiceUnavailableError as exc:
                # TODO: [DECISIÓN DE NEGOCIO PENDIENTE] SOFIAPLUS_FALLBACK_POLICY
                # Define qué hacer si el servicio externo del SENA no responde durante el registro
                policy = getattr(settings, 'SOFIAPLUS_FALLBACK_POLICY', 'ALLOW_PENDING')
                if policy == 'ALLOW_PENDING':
                    # Registro provisional sin verificación
                    self._verificado_sofia_plus = False
                    self._fecha_verificacion = None
                else:
                    self.add_error(
                        None,
                        'El servicio de verificación de SofiaPlus no está disponible en este momento. '
                        'Por favor intenta nuevamente en unos minutos.'
                    )

            except SofiaPlusInvalidInputError as exc:
                self.add_error('documento', exc.user_friendly_message)

            except SofiaPlusError as exc:
                # Error genérico del servicio
                policy = getattr(settings, 'SOFIAPLUS_FALLBACK_POLICY', 'ALLOW_PENDING')
                if policy == 'ALLOW_PENDING':
                    self._verificado_sofia_plus = False
                    self._fecha_verificacion = None
                else:
                    self.add_error(None, exc.user_friendly_message)

        return cd

    def save(self):
        cd = self.cleaned_data
        nombre_completo = f"{cd['first_name']} {cd['last_name']}".strip()
        partes = nombre_completo.split(' ', 1)
        p_nombre = partes[0]
        p_apellido = partes[1] if len(partes) > 1 else ''

        verificado = getattr(self, '_verificado_sofia_plus', False)
        fecha_verif = getattr(self, '_fecha_verificacion', None)

        usuario = Usuario(
            documento=cd['documento'],
            tipo_documento=cd['tipo_documento'],
            primer_nombre=p_nombre,
            primer_apellido=p_apellido,
            correo_personal=cd['email'],
            telefono='',
            ficha=cd.get('numero_ficha', ''),
            programa=cd.get('nombre_programa', ''),
            password=make_password(cd['password1']),
            rol='Usuario',  # Rol estrictamente forzado en backend
            verificado_sofia_plus=verificado,
            fecha_verificacion=fecha_verif,
        )
        usuario.save()
        return usuario


class EditarUsuarioAdminForm(forms.ModelForm):
    nombre_completo = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nueva_password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Dejar en blanco para no cambiar'})
    )

    class Meta:
        model = Usuario
        fields = [
            'correo_personal',
            'telefono',
            'ficha',
            'programa',
            'rol',
        ]
        widgets = {
            'correo_personal': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ficha': forms.TextInput(attrs={'class': 'form-control'}),
            'programa': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nombre_completo'].initial = self.instance.nombre_completo

    def clean_correo_personal(self):
        correo = self.cleaned_data.get('correo_personal', '').strip().lower()
        if not correo:
            raise ValidationError('El correo no puede estar vacío.')
        qs = Usuario.objects.filter(correo_personal=correo).exclude(documento=self.instance.documento)
        if qs.exists():
            raise ValidationError('Ese correo ya está en uso por otro usuario.')
        return correo

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '').strip()
        if tel and not tel.isdigit():
            raise ValidationError('El teléfono solo debe contener números.')
        return tel

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        roles_validos = [r[0] for r in Usuario.ROL_CHOICES]
        if rol not in roles_validos:
            raise ValidationError('Rol no válido.')
        return rol

    def save(self, commit=True):
        usuario = self.instance
        cd = self.cleaned_data
        usuario.nombre_completo = cd.get('nombre_completo', usuario.nombre_completo)
        usuario.correo_personal = cd.get('correo_personal')
        usuario.telefono = cd.get('telefono')
        usuario.ficha = cd.get('ficha')
        usuario.programa = cd.get('programa')
        usuario.rol = cd.get('rol')
        nueva_pass = cd.get('nueva_password')
        if nueva_pass:
            usuario.password = make_password(nueva_pass)
        if commit:
            usuario.save()
        return usuario


class PerfilUsuarioForm(forms.ModelForm):
    nombre_completo = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = [
            'correo_personal',
            'telefono',
            'ficha',
            'programa',
        ]
        widgets = {
            'correo_personal': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ficha': forms.TextInput(attrs={'class': 'form-control'}),
            'programa': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nombre_completo'].initial = self.instance.nombre_completo

    def clean_correo_personal(self):
      correo = (self.cleaned_data.get('correo_personal') or '').strip().lower()
      if not correo:
          raise ValidationError('El correo no puede estar vacío.')
      qs = Usuario.objects.filter(correo_personal=correo).exclude(documento=self.instance.documento)
      if qs.exists():
          raise ValidationError('Este correo ya está en uso por otro usuario.')
      return correo

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '').strip()
        if tel and not tel.isdigit():
            raise ValidationError('El teléfono solo debe contener números.')
        return tel

    def save(self, commit=True):
        usuario = self.instance
        cd = self.cleaned_data
        usuario.nombre_completo = cd.get('nombre_completo', usuario.nombre_completo)
        usuario.correo_personal = cd.get('correo_personal')
        usuario.telefono = cd.get('telefono')
        usuario.ficha = cd.get('ficha')
        usuario.programa = cd.get('programa')
        if commit:
            usuario.save()
        return usuario


class CambiarPasswordForm(forms.Form):
    password_actual = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña actual'})
    )
    password_nueva = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres'})
    )
    password_confirma = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite la nueva contraseña'})
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_password_actual(self):
        actual = self.cleaned_data.get('password_actual')
        if not check_password(actual, self.usuario.password):
            raise ValidationError('La contraseña actual es incorrecta.')
        return actual

    def clean(self):
        cd = super().clean()
        p1 = cd.get('password_nueva')
        p2 = cd.get('password_confirma')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirma', 'Las contraseñas no coinciden.')
        return cd

    def save(self):
        self.usuario.password = make_password(self.cleaned_data['password_nueva'])
        self.usuario.save(update_fields=['password'])
        return self.usuario