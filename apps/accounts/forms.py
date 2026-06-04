from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from uuid import uuid4
from .models import UserProfile


def _username_interno(email):
    if len(email) <= 150 and not User.objects.filter(username=email).exists():
        return email

    base = email.split("@", 1)[0][:120] or "usuario"
    while True:
        candidato = f"{base}-{uuid4().hex[:12]}"[:150]
        if not User.objects.filter(username=candidato).exists():
            return candidato


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-mail")
    first_name = forms.CharField(max_length=50, required=True, label="Nome")
    last_name = forms.CharField(max_length=50, required=True, label="Sobrenome")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({
            "autocomplete": "email",
            "inputmode": "email",
        })
        self.fields["password1"].widget.attrs.update({"autocomplete": "new-password"})
        self.fields["password2"].widget.attrs.update({"autocomplete": "new-password"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = _username_interno(self.cleaned_data["email"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "inputmode": "email",
        }),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "E-mail ou senha inválidos.",
        "inactive": "Esta conta está inativa.",
        "duplicate_email": "Há mais de uma conta com este e-mail. Contate o suporte.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password")

        if email and password:
            usuarios = User.objects.filter(email__iexact=email)
            if not usuarios.exists():
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            if usuarios.count() > 1:
                raise forms.ValidationError(
                    self.error_messages["duplicate_email"],
                    code="duplicate_email",
                )

            usuario = usuarios.first()
            self.user_cache = authenticate(
                self.request,
                username=usuario.get_username(),
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )

        return cleaned_data

    def get_user(self):
        return self.user_cache


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, label="Nome")
    last_name = forms.CharField(max_length=50, label="Sobrenome")
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = UserProfile
        fields = ("telefone", "bio", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        email = self.cleaned_data["email"].strip().lower()
        profile.user.first_name = self.cleaned_data["first_name"]
        profile.user.last_name = self.cleaned_data["last_name"]
        profile.user.email = email
        if commit:
            profile.user.save()
            profile.save()
        return profile

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.instance.user_id)
            .exists()
        ):
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email
