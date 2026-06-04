# Campo: Meses até Título (meses_titulo)

## Definição
Número de meses até o recebimento do título aquisitivo do imóvel após a arrematação em leilão.

## Localização
- **Modelo**: `apps/imoveis/models.py` - Campo `meses_titulo` (PositiveIntegerField, default=0)
- **Formulário**: `apps/imoveis/forms.py` - Seção "Prazos e Títulos"
- **Templates**: 
  - `templates/imoveis/form.html` - Seção 7.5 "Prazos e Títulos"
  - `templates/calculadora/index.html` - Campo oculto com padrão de 3 meses

## Funcionalidades e Aplicabilidade

### 1. Cálculo de Gastos Mensais
**Arquivo**: `core/calculos/motor.py` (função `calcular`)

```python
meses_ef = max(meses_giro - meses_titulo, 0)
tot_iptu = iptu_am * meses_ef
tot_cond = cond_am * meses_ef
tot_aluguel = rec_aluguel_am * meses_ef
```

**Funcionalidade**: Calcula o período efetivo em que o investidor é responsável pelos gastos:
- **IPTU mensal**: Só é contabilizado APÓS receber o título
- **Condomínio mensal**: Só é contabilizado APÓS receber o título
- **Receita aluguel**: Só é contabilizada APÓS receber o título

**Exemplo**:
- Giro padrão: 12 meses
- Meses até título: 3 meses
- **Resultado**: Meses efetivos = 12 - 3 = 9 meses
- IPTU (R$ 100/mês) = 100 × 9 = R$ 900
- Se não tivesse meses_titulo, seria: 100 × 12 = R$ 1.200

### 2. Impacto no ROI e Rentabilidade
O campo reduz:
- Custos de manutenção (IPTU, condomínio)
- Tempo até receber receitas (aluguel)
- Resultando em melhor rentabilidade durante o período de retenção

### 3. Integração com Calculadora
**Arquivo**: `templates/calculadora/index.html`
- Valor padrão: **3 meses**
- Campo: `<input type="hidden" name="meses_titulo" value="3">`
- Pode ser alterado dinamicamente para simular diferentes cenários

## Fluxo de Dados

```
Formulário de Imóvel
    ↓
[Campo: meses_titulo]
    ↓
Modelo Imovel.meses_titulo
    ↓
view criar() / editar()
    ↓
Imovel.to_calc_dict()
    ↓
calcular(p) - motor.py
    ↓
meses_ef = meses_giro - meses_titulo
    ↓
Cálculo de custos/receitas mensais
    ↓
ROI e Resultado Final
```

## Validação
- **Tipo**: PositiveIntegerField
- **Padrão**: 0 (sem período de espera)
- **Intervalo comum**: 0 a 6 meses
- **Validação**: Não há validação no formulário (aceita qualquer inteiro positivo)

## Casos de Uso

| Cenário | Meses até Título | Motivo |
|---------|------------------|--------|
| Leilão Extrajudicial rápido | 0-1 | Registro rápido |
| Leilão Judicial padrão | 2-3 | Processamento normal |
| Perícia ou recursos pendentes | 4-6 | Atrasos adicionais |
| Financiamento com bancário | 3-4 | Processamento bancário |

## Referências Cruzadas
- Relacionado: `giro_padrao` (meses de giro padrão para simulação)
- Afeta: IPTU, condomínio, receita aluguel, ROI, resultado final
- Usado em: `to_calc_dict()` do modelo Imovel

