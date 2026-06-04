from django import forms
from decimal import Decimal, InvalidOperation
from .models import Imovel


SELECT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent bg-white"
)

# Campo de texto simples (endereço, obs, etc.)
TEXT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
)

# Campos monetários e percentuais usam TextInput + IMask via data-imask
# A formatação visual é feita pelo JS; o valor submetido ao servidor é o hidden.
# No form.html, esses campos são renderizados com wrapper (prefix/suffix).
def money_widget():
    return forms.TextInput(attrs={
        "data-imask": "money",
        "placeholder": "0,00",
        "class": "flex-1 px-3 py-2 text-sm outline-none bg-white border-none min-w-0",
        "autocomplete": "off",
    })

def pct_widget():
    return forms.TextInput(attrs={
        "data-imask": "pct",
        "placeholder": "0,00",
        "class": "flex-1 px-3 py-2 text-sm outline-none bg-white border-none min-w-0",
        "autocomplete": "off",
    })

def int_widget():
    return forms.NumberInput(attrs={
        "class": TEXT_CLASS,
        "min": "0",
    })


class ImovelForm(forms.ModelForm):
    class Meta:
        model = Imovel
        exclude = ("user", "id", "data_cadastro", "updated_at")
        widgets = {
            # Identificação
            "endereco":         forms.TextInput(attrs={"class": TEXT_CLASS, "placeholder": "Ex: Rua das Acácias, 123"}),
            "cidade":           forms.TextInput(attrs={"class": TEXT_CLASS, "placeholder": "Ex: Salvador"}),
            "estado":           forms.Select(attrs={"class": SELECT_CLASS}),
            "etapa":            forms.Select(attrs={"class": SELECT_CLASS}),
            "tipo_leilao":      forms.Select(attrs={"class": SELECT_CLASS}),
            "obs":              forms.Textarea(attrs={"class": TEXT_CLASS, "rows": 3}),
            # Leilão — monetário
            "avaliacao":        money_widget(),
            "lance":            money_widget(),
            # Pagamento
            "tipo_pgto":        forms.Select(attrs={"class": SELECT_CLASS}),
            "entrada":          pct_widget(),
            "prazo_fin":        int_widget(),
            "cet_aa":           pct_widget(),
            # Receitas — monetário / percentual
            "preco_venda":      money_widget(),
            "taxa_acrescimo":   pct_widget(),
            "desconto_venda":   pct_widget(),
            "rec_aluguel_am":   money_widget(),
            "pct_corretor":     pct_widget(),
            # ITBI
            "pct_itbi_base":    forms.Select(attrs={"class": SELECT_CLASS}),
            "aliq_itbi":        pct_widget(),
            "aliq_itbi_fin":    pct_widget(),
            # Cartório
            "modo_cartorio":    forms.Select(attrs={"class": SELECT_CLASS}),
            "av_fiscal":        money_widget(),
            "escritura_manual": money_widget(),
            "registro_manual":  money_widget(),
            "pct_leiloeiro":    pct_widget(),
            # Despesas
            "reformas":         money_widget(),
            "custo_desocup":    money_widget(),
            "debitos":          money_widget(),
            "despesas_div":     money_widget(),
            "laudemio_pct":     pct_widget(),
            "meses_titulo":     int_widget(),
            # Recorrentes
            "iptu_am":          money_widget(),
            "cond_am":          money_widget(),
            # Oportunidade & IR
            "custo_oport_aa":   pct_widget(),
            "tipo_pessoa":      forms.Select(attrs={"class": SELECT_CLASS}),
            # Simulação
            "lucro_minimo":     money_widget(),
            "incremento_lance": money_widget(),
            "giro_padrao":      forms.Select(attrs={"class": SELECT_CLASS}),
        }
        labels = {
            "taxa_acrescimo":   "Acréscimo sobre venda (%)",
            "desconto_venda":   "Desconto sobre venda (%)",
            "pct_itbi_base":    "Base de cálculo ITBI",
            "aliq_itbi_fin":    "Alíq. fração financiada (%)",
            "av_fiscal":        "Avaliação fiscal / valor venal IPTU (R$)",
            "custo_desocup":    "Custo de desocupação (R$)",
            "meses_titulo":     "Meses até título aquisitivo",
            "custo_oport_aa":   "Rendimento alternativo (% a.a.)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna todos os campos opcionais no formulário (eles têm defaults no model)
        for field_name in self.fields:
            self.fields[field_name].required = False

    def _clean_br_decimal(self, field_name):
        """Converte formato BR (303.000,00) para Decimal aceito pelo Django."""
        value = self.data.get(field_name, '')
        if not value:
            return Decimal('0')
        try:
            cleaned = str(value).replace('.', '').replace(',', '.')
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal('0')

    # Sobrescreve clean para campos que o IMask pode enviar no formato BR
    _MONEY_FIELDS = [
        'avaliacao', 'lance', 'preco_venda', 'rec_aluguel_am', 'av_fiscal',
        'escritura_manual', 'registro_manual', 'reformas', 'custo_desocup',
        'debitos', 'despesas_div', 'iptu_am', 'cond_am',
        'lucro_minimo', 'incremento_lance',
    ]
    _PCT_FIELDS = [
        'entrada', 'cet_aa', 'taxa_acrescimo', 'desconto_venda', 'pct_corretor',
        'aliq_itbi', 'aliq_itbi_fin', 'pct_leiloeiro', 'laudemio_pct', 'custo_oport_aa',
    ]
    _INT_FIELDS = [
        'prazo_fin', 'meses_titulo', 'giro_padrao',
    ]

    def clean(self):
        cleaned = super().clean()

        # Processa campos monetários e percentuais
        for fname in self._MONEY_FIELDS + self._PCT_FIELDS:
            raw = self.data.get(fname, '').strip()

            # Se vazio, deixa para o model usar o default
            if not raw:
                if fname in cleaned:
                    del cleaned[fname]
                continue

            try:
                # Trata formato brasileiro (1.000,50) e internacional (1000.50)
                v = raw
                if ',' in v:
                    v = v.replace('.', '').replace(',', '.')
                cleaned[fname] = Decimal(v)
            except (InvalidOperation, ValueError, TypeError):
                # Se falhar, deixa para o model usar o default
                if fname in cleaned:
                    del cleaned[fname]

        # Processa campos inteiros
        for fname in self._INT_FIELDS:
            raw = self.data.get(fname, '').strip()

            # Se vazio, deixa para o model usar o default
            if not raw:
                if fname in cleaned:
                    del cleaned[fname]
                continue

            try:
                cleaned[fname] = int(raw)
            except (ValueError, TypeError):
                # Se falhar, deixa para o model usar o default
                if fname in cleaned:
                    del cleaned[fname]

        return cleaned
