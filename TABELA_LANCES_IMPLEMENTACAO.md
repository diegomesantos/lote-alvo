# Tabela de Lances Progressivos — Implementação

## Descrição
Implementação de uma tabela interativa que mostra simulações de ROI para múltiplos lances progressivos, seguindo incrementos configuráveis.

## Funcionalidade

### Como Funciona
1. **Valor inicial de Lance**: Começa com o lance base configurado
2. **Incremento**: Aumenta progressivamente em passos definidos (padrão: R$ 5.000)
3. **Simulações**: Para cada lance, calcula o ROI em diferentes períodos (1, 3, 4, 6, 7, 9, 10, 12 meses)
4. **Visualização**: Tabela colorida mostrando ROI, com cores indicando rentabilidade

## Arquitetura

### 1. Motor de Cálculo (`core/calculos/motor.py`)

**Função**: `tabela_lances(p)`
- Gera lances progressivos a partir do lance inicial
- Para cada lance, calcula ROI em todos os períodos
- Retorna lista de dicts com estrutura:
  ```python
  {
    "lance": 300000,
    "resultado_por_giro": {
      1: {...resultado detalhado...},
      3: {...},
      12: {...}
    }
  }
  ```

### 2. View (`apps/calculadora/views.py`)

**Função**: `tabela_lances_view(request)`
- Recebe parametros do formulário (POST)
- Chama `tabela_lances()` do motor
- Formata resultado em HTML
- Retorna JSON com:
  - `success`: boolean
  - `html`: linhas da tabela em HTML
  - `giro_meses`: períodos disponíveis

### 3. Template (`templates/calculadora/resultado_htmx.html`)

**Componentes**:
- Botão: "Ver tabela de lances progressivos"
- Modal HTML5: `<dialog id="modal-lances">`
- JavaScript: `carregarTabelaLances()` - Carrega dados via AJAX

### 4. URLs (`apps/calculadora/urls.py`)

```python
path("tabela-lances/", views.tabela_lances_view, name="tabela_lances")
```

## Cálculo Explicado

### Exemplo Prático
```
Lance Base: R$ 300.000
Incremento: R$ 5.000
Preço Venda: R$ 420.000
Giro Padrão: 12 meses

Simulação:
├─ Lance 1: R$ 300.000 → ROI 12m = 18,90%
├─ Lance 2: R$ 305.000 → ROI 12m = 17,23%
├─ Lance 3: R$ 310.000 → ROI 12m = 15,60%
└─ ... até o lance máximo ou limite
```

### Fórmula do ROI
```
ROI = (Resultado Final / Investimento Inicial) × 100
```

Onde:
- **Investimento Inicial** = Lance + Cartório + Reformas + Desocupação + Outras despesas
- **Resultado Final** = Receita - Custos Cartório - Custos Operacionais

## Colorização

| Cor | ROI | Significado |
|-----|-----|------------|
| 🟩 Verde | ≥ 15% | Excelente rentabilidade |
| 🟨 Amarelo | 0-15% | Rentabilidade moderada |
| 🟥 Vermelho | < 0% | Prejuízo estimado |

## Fluxo de Dados

```
Formulário da Calculadora
  ↓
[Clica "Ver tabela de lances"]
  ↓
JavaScript carregarTabelaLances()
  ↓
POST /calculadora/tabela-lances/
  ↓
View tabela_lances_view()
  ↓
Motor: tabela_lances()
  ↓
Para cada lance:
  ├─ Cria cópia de parâmetros com novo lance
  ├─ Chama tabela_giro() para todos os períodos
  └─ Coleta resultados
  ↓
Retorna JSON com HTML
  ↓
JavaScript monta tabela no modal
  ↓
Modal exibido ao usuário
```

## Como Usar

1. Acesse `/calculadora/`
2. Preencha o formulário com os parâmetros desejados
3. Configure o "Incremento de Lance" (padrão: 5000)
4. Clique em "Calcular" para ver o resumo
5. Clique em "📊 Ver tabela de lances progressivos"
6. Modal abre com tabela interativa

## Customizações Possíveis

### 1. Número de Lances
Editar em `core/calculos/motor.py`:
```python
# Aumentar limite de lances (atualmente 20)
limite = min(lance_maximo_val + incremento, lance_inicial + (20 * incremento))
```

### 2. Cores e Estilos
Editar em `apps/calculadora/views.py` na função `tabela_lances_view()`:
```python
# Ajustar thresholds de cor
if roi >= 15:
    cor_classe = "bg-green-100 text-green-900"
```

### 3. Campos Exibidos
Atualmente mostra apenas ROI. Possível adicionar:
- Resultado em R$
- Taxa mensal equivalente
- Período de payback

## Testes Realizados

✅ Função `tabela_lances()` gera múltiplos lances corretamente
✅ View `tabela_lances_view()` retorna JSON válido
✅ HTML da tabela é gerado com colorização
✅ Modal aparece na página de resultado
✅ JavaScript carrega dados sem erros
✅ Tabela é responsiva e navegável

## Referências

- Inspirado em: https://[site-original]
- Função base: `motor.calcular()`
- Períodos de giro: `GIRO_MESES = [1, 3, 4, 6, 7, 9, 10, 12]`

