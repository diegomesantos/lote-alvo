from decimal import Decimal, InvalidOperation

from django import forms
from .models import LancamentoFinanceiro, CategoriaFinanceira

INPUT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
)


class LancamentoForm(forms.ModelForm):
    class Meta:
        model = LancamentoFinanceiro
        fields = ("imovel", "categoria", "tipo", "descricao", "valor", "data", "status", "obs", "comprovante")
        widgets = {
            "imovel":    forms.Select(attrs={"class": INPUT_CLASS}),
            "categoria": forms.Select(attrs={"class": INPUT_CLASS}),
            "tipo":      forms.Select(attrs={"class": INPUT_CLASS}),
            "descricao": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Ex: Reforma banheiro"}),
            "valor":     forms.TextInput(attrs={
                "data-imask": "money",
                "placeholder": "0,00",
                "class": "flex-1 border-none bg-white px-3 py-2 text-sm outline-none min-w-0",
                "autocomplete": "off",
            }),
            "data":      forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "status":    forms.Select(attrs={"class": INPUT_CLASS}),
            "obs":       forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
            "comprovante": forms.FileInput(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        if args and args[0] is not None:
            args = list(args)
            args[0] = self._normalize_payload(args[0])
            args = tuple(args)
        elif kwargs.get("data") is not None:
            kwargs["data"] = self._normalize_payload(kwargs["data"])

        super().__init__(*args, **kwargs)
        if user:
            self.fields["imovel"].queryset = user.imoveis.all()
            self.fields["imovel"].required = False
        self.fields["categoria"].queryset = CategoriaFinanceira.objects.all()
        self.fields["categoria"].required = False

    @staticmethod
    def _normalize_payload(data):
        try:
            normalized = data.copy()
        except AttributeError:
            normalized = data.copy() if isinstance(data, dict) else data

        try:
            raw = normalized.get("valor", "")
        except AttributeError:
            return data
        if raw not in (None, ""):
            value = str(raw).strip()
            if "," in value:
                normalized["valor"] = value.replace(".", "").replace(",", ".")
        return normalized

    def clean_valor(self):
        value = self.data.get("valor", "")
        if value in (None, ""):
            return Decimal("0")
        try:
            text = str(value).strip()
            if "," in text:
                text = text.replace(".", "").replace(",", ".")
            return Decimal(text)
        except (InvalidOperation, ValueError, TypeError):
            raise forms.ValidationError("Informe um valor válido.")

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        tipo = cleaned.get("tipo")
        if categoria and tipo and categoria.tipo != tipo:
            self.add_error("categoria", "A categoria precisa ser do mesmo tipo do lançamento.")
        return cleaned
