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
            "valor":     forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01", "min": "0"}),
            "data":      forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "status":    forms.Select(attrs={"class": INPUT_CLASS}),
            "obs":       forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
            "comprovante": forms.FileInput(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["imovel"].queryset = user.imoveis.all()
            self.fields["imovel"].required = False
