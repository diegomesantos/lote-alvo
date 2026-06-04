from django import forms
from .models import ImovelCaixa


class FiltrosLeiloesForm(forms.Form):
    q = forms.CharField(required=False, label='Buscar')
    estados = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    cidades = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    tipos = forms.MultipleChoiceField(
        required=False,
        choices=ImovelCaixa.TIPO_CHOICES,
        widget=forms.CheckboxSelectMultiple
    )
    valor_min = forms.DecimalField(required=False)
    valor_max = forms.DecimalField(required=False)
    desconto = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Qualquer desconto'),
            ('0-10', '0-10%'),
            ('10-20', '10-20%'),
            ('20-30', '20-30%'),
            ('30+', '30%+'),
        ]
    )
    financiamento = forms.BooleanField(required=False)
    fgts = forms.BooleanField(required=False)
    consorcio = forms.BooleanField(required=False)
