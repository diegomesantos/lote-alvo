# LoteAlvo Django — Contexto Completo do Projeto

## O que é este projeto

Versão profissional e escalável do LoteAlvo, reescrita do zero em **Django + HTMX + Tailwind CSS** para ir a produção no Railway com suporte a múltiplos usuários e modelo de assinatura.

O protótipo original (pasta `leilao_app/`) foi desenvolvido em Streamlit para estudo/prototipagem. Esta versão é a definitiva para produção.

---

## Por que migramos do Streamlit para Django

O Streamlit foi perfeito para prototipar, mas tem limitações estruturais para SaaS multi-usuário:

| Limitação Streamlit | Como Django resolve |
|---|---|
| Multi-usuário é gambiarra | Auth nativo + sessions + PostgreSQL |
| Sem URL routing real | URLs limpas `/kanban/`, `/imoveis/<id>/` |
| Kanban drag-drop impossível | SortableJS + HTMX |
| Sem assinatura/stripe | Django models + integração futura |
| Rerun completo a cada clique | HTMX substitui só o fragment HTML |
| Performance com muitos users | WSGI/Gunicorn + PostgreSQL |

---

## Stack tecnológica

- **Django 5.0.6** — framework principal (MVT)
- **HTMX 1.9** — requisições parciais sem JavaScript (calculadora live)
- **Alpine.js 3.x** — reatividade client-side leve (campos condicionais)
- **Tailwind CSS** (CDN) — design system utility-first
- **SortableJS 1.15** — drag-and-drop do Kanban
- **WhiteNoise 6.7** — serving de arquivos estáticos em produção
- **Gunicorn** — servidor WSGI para produção
- **SQLite** (local) / **PostgreSQL** (Railway)
- **python-decouple** — gerenciamento de variáveis de ambiente

---

## Estrutura de arquivos

```
smart_leilao/
├── .venv/                    ← ambiente virtual Python (NÃO committar)
├── .gitignore
├── .env.example              ← copie para .env em produção
├── manage.py
├── Procfile                  ← Railway/Heroku: gunicorn config.wsgi
├── railway.toml              ← configuração Railway (migrate + start)
├── requirements.txt          ← produção (inclui psycopg2)
├── requirements-dev.txt      ← desenvolvimento local (SQLite, sem psycopg2)
│
├── config/
│   ├── settings/
│   │   ├── base.py           ← configurações comuns
│   │   ├── development.py    ← DEBUG=True, SQLite
│   │   └── production.py     ← DEBUG=False, PostgreSQL, HTTPS
│   ├── urls.py               ← roteamento principal
│   └── wsgi.py
│
├── apps/
│   ├── accounts/             ← autenticação e perfis
│   │   ├── models.py         ← UserProfile (plano Free/Pro)
│   │   ├── views.py          ← registro, login, logout, perfil
│   │   ├── forms.py
│   │   └── urls.py
│   │
│   ├── imoveis/              ← CRUD de imóveis + Kanban
│   │   ├── models.py         ← Imovel (todos os campos da calculadora)
│   │   ├── views.py          ← kanban, listar, detalhe, criar, editar, excluir
│   │   ├── forms.py          ← ImovelForm com widgets Tailwind
│   │   └── urls.py
│   │
│   ├── calculadora/          ← calculadora standalone
│   │   ├── views.py          ← index (página) + calcular_htmx (endpoint POST)
│   │   └── urls.py
│   │
│   └── financeiro/           ← gestão financeira
│       ├── models.py         ← CategoriaFinanceira, LancamentoFinanceiro
│       ├── views.py          ← dashboard, novo_lancamento, editar, excluir
│       ├── forms.py
│       └── urls.py
│
├── core/
│   ├── calculos/
│   │   ├── motor.py          ← calcular(), SAC, IR, custo oportunidade
│   │   └── cartorio.py       ← tabelas emolumentos 12 estados
│   └── templatetags/
│       └── leilao_tags.py    ← filtros: brl, brl_short, pct, dict_get
│
├── templates/
│   ├── base.html             ← layout principal com sidebar dark
│   ├── accounts/             ← login.html, registro.html, perfil.html
│   ├── imoveis/              ← kanban.html, lista.html, form.html, detalhe.html
│   ├── calculadora/          ← index.html, resultado_htmx.html
│   ├── financeiro/           ← dashboard.html, form_lancamento.html
│   └── components/           ← tabela_giro.html
│
└── static/                   ← arquivos estáticos customizados (se houver)
```

---

## Como rodar localmente

```bash
# 1. Entre na pasta do projeto
cd smart_leilao

# 2. Ative o ambiente virtual
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. Instale dependências (dev — sem PostgreSQL)
pip install -r requirements-dev.txt

# 4. Crie o banco e aplique as migrations
python manage.py migrate

# 5. Crie seu usuário
python manage.py createsuperuser

# 6. Rode o servidor
python manage.py runserver

# Acesse: http://127.0.0.1:8000
```

**Usuário de teste já criado:** `diego` / `leilao123`

---

## URLs principais

| URL | View | Descrição |
|---|---|---|
| `/` | redirect | → `/kanban/` |
| `/accounts/login/` | entrar | Tela de login |
| `/accounts/registro/` | registro | Criar conta |
| `/kanban/` | kanban | Board com 6 colunas |
| `/kanban/lista/` | listar | Grid de todos os imóveis |
| `/kanban/novo/` | criar | Formulário novo imóvel |
| `/kanban/<uuid>/` | detalhe | Detalhe + simulação completa |
| `/kanban/<uuid>/editar/` | editar | Editar imóvel |
| `/kanban/<uuid>/etapa/` | atualizar_etapa | HTMX drag-and-drop |
| `/calculadora/` | calculadora | Calculadora standalone |
| `/calculadora/calcular/` | calcular_htmx | Endpoint HTMX (POST) |
| `/financeiro/` | dashboard | Gestão financeira |
| `/financeiro/lancamento/novo/` | novo_lancamento | Novo lançamento |
| `/admin/` | django admin | Painel admin |

---

## Motor de cálculo (portado sem alteração do protótipo)

### `core/calculos/motor.py`

Todas as funções são Python puro, sem dependência de UI:

```python
calcular(p: dict, meses_giro: int) -> dict
    # p = dicionário com todos os parâmetros do imóvel
    # Retorna: lance, preco_venda, val_inicial, itbi, escritura, registro,
    #          com_leil, laudemio, reformas, ir, resultado, roi, tem,
    #          roi_custo, tem_custo, custo_total, custo_ate_venda

tabela_giro(p: dict) -> dict[int, dict]
    # Retorna {1: resultado_1m, 3: resultado_3m, ..., 12: resultado_12m}

lance_maximo(p: dict) -> float | None
    # Estima lance máximo para atingir lucro mínimo desejado
```

### Fórmulas importantes

**Base cartório:** `max(lance, av_fiscal)` — lei TJ-BA e outros (confirmado via legislação)

**IR Ganho de Capital PF:**
- Até R$ 5M: 15%
- R$ 5M–10M: 17,5%
- R$ 10M–30M: 20%
- Acima R$ 30M: 22,5%
- PJ: 15% flat

**SAC:** Amortização constante com juros decrescentes sobre saldo devedor

**ROI capital próprio** (nosso método): `resultado ÷ (val_entrada + custos obrigatórios)`
**ROI custo até venda** (método operacional): `resultado ÷ custo_ate_venda`

### `core/calculos/cartorio.py`

Tabelas oficiais de emolumentos para 12 estados:
- **BA** — TJ-BA (tabela II e III idênticas — Lei Estadual nº 12.373/2011)
- SP, RJ (+ FUNDPERJ 0,1%), MG, PR (+ FUNREJUS 0,2%), RS, PE, CE, DF, SC, GO, ES
- Estados sem tabela: estimativa 0,5% do valor

---

## Como funciona o Kanban drag-and-drop

```javascript
// kanban.html — SortableJS configura cada coluna
Sortable.create(col, {
  group: 'kanban',       // permite arrastar entre colunas
  animation: 200,
  onEnd: function(evt) {
    const cardId = evt.item.dataset.id;     // UUID do imóvel
    const novaEtapa = evt.to.dataset.etapa; // slug da etapa destino
    
    // HTMX-style: POST manual para /kanban/<uuid>/etapa/
    fetch(`/kanban/${cardId}/etapa/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'HX-Request': 'true' },
      body: `etapa=${novaEtapa}`,
    });
  }
});
```

---

## Como funciona a Calculadora HTMX

```html
<!-- calculadora/index.html -->
<form id="calc-form"
      hx-post="/calculadora/calcular/"   <!-- endpoint Django -->
      hx-target="#resultado-panel"        <!-- onde substituir o HTML -->
      hx-trigger="change delay:500ms, submit">  <!-- recalcula 500ms após qualquer mudança -->
```

O endpoint `calcular_htmx` processa o POST, roda `tabela_giro()` e retorna apenas o HTML do painel de resultados (`resultado_htmx.html`). Zero JavaScript de cálculo.

---

## Deploy no Railway

### Passo a passo

1. **Crie um repositório GitHub** com este projeto (não commitar `.venv/`, `db.sqlite3`, `.env`)

2. **No Railway:** New Project → Deploy from GitHub → seleciona o repo

3. **Adicione PostgreSQL:** clique em `+` → Add Service → PostgreSQL
   - Railway injeta `DATABASE_URL` automaticamente no ambiente

4. **Variáveis de ambiente** (Settings → Variables):
   ```
   SECRET_KEY=<gere uma chave aleatória>
   DJANGO_SETTINGS_MODULE=config.settings.production
   ALLOWED_HOSTS=*.railway.app
   ```

5. **O `railway.toml` já configura tudo:**
   ```toml
   [deploy]
   startCommand = "python manage.py migrate --settings=config.settings.production && gunicorn config.wsgi"
   ```

### Gerar SECRET_KEY

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Modelo de dados — Imovel

Campos completos (todos mapeados para o motor de cálculo):

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | UUID | Chave primária automática |
| `user` | FK User | Dono do imóvel (multi-tenant) |
| `endereco`, `cidade`, `estado` | CharField | Localização |
| `etapa` | CharField | oportunidade/arrematado/documentacao/reforma/a_venda/concluido |
| `tipo_leilao` | CharField | Extrajudicial / Judicial |
| `avaliacao`, `lance` | Decimal | Valores do leilão |
| `tipo_pgto` | CharField | À Vista / Financiamento SAC |
| `entrada`, `prazo_fin`, `cet_aa` | Decimal/Int | Parâmetros SAC |
| `preco_venda`, `pct_corretor` | Decimal | Receita na venda |
| `taxa_acrescimo`, `desconto_venda` | Decimal | Ajuste sobre preço base |
| `aliq_itbi`, `pct_itbi_base` | Decimal/CharField | ITBI |
| `av_fiscal`, `modo_cartorio` | Decimal/CharField | Base cartório |
| `pct_leiloeiro` | Decimal | Comissão leiloeiro |
| `reformas`, `custo_desocup`, `debitos`, `despesas_div` | Decimal | Despesas |
| `laudemio_pct`, `meses_titulo` | Decimal/Int | Laudêmio + prazo posse |
| `iptu_am`, `cond_am` | Decimal | Gastos mensais |
| `custo_oport_aa`, `tipo_pessoa` | Decimal/CharField | IR e custo oportunidade |
| `lucro_minimo`, `incremento_lance` | Decimal | Parâmetros de simulação |
| `giro_padrao` | Int | Prazo padrão de simulação (meses) |

---

## Decisões técnicas tomadas nesta conversa

### Por que Tailwind via CDN (sem build)?
Evita dependência de Node.js/npm para um projeto Python. O CDN do Tailwind v3 é suficiente para produção neste estágio — quando o volume de CSS crescer, migra para o standalone CLI.

### Por que HTMX em vez de React/Vue?
O motor de cálculo é Python. Com HTMX, os cálculos rodam no servidor (Django view) e apenas o HTML de resultado volta pro browser. Zero duplicação de lógica. Zero JavaScript de negócio.

### Por que SortableJS direto (sem biblioteca wrapper)?
A integração é trivial: captura o evento `onEnd` e dispara um `fetch()` manual para o endpoint HTMX. Menos dependências = menos problemas.

### Base de cálculo cartório: `max(lance, av_fiscal)`
Confirmado via CONTEXT.md do protótipo e legislação brasileira (TJ-BA Lei Estadual nº 12.373/2011 e demais estados):
> "A base de cálculo para emolumentos é o maior entre o valor declarado do negócio e o valor venal do IPTU."

### Escritura = 0 em Financiamento SAC e Leilão Judicial
Contrato bancário e carta de arrematação substituem a escritura pública — confirmado.

---

## Próximos passos (backlog priorizado)

### Alta prioridade
- [ ] Atualizar tabelas cartoriais BA 2026 (TJ-BA publicou em dez/2025)
- [ ] Adicionar tabelas dos 15 estados restantes (AM, PA, MA, PI, RN, PB, AL, SE, MS, MT, RO, AC, AP, RR, TO)
- [ ] Upload de foto de capa por imóvel
- [ ] Exportar simulação como PDF

### Média prioridade
- [ ] Integração Stripe para plano Pro (assinatura R$ 49/mês)
- [ ] "Tabela de lances" — simular múltiplos lances e ver qual maximiza ROI
- [ ] Gráfico de resultado por prazo de giro (Chart.js ou Recharts)
- [ ] Modo escuro

### Baixa prioridade
- [ ] Import de imóveis do data.json do protótipo Streamlit
- [ ] Notificações por e-mail (mudança de etapa, alertas)
- [ ] API REST para futura app mobile

---

## Referência do projeto original

Arquivos HTML da interface de referência salvos em `leilao_app/Modelos/`:
- `Referência original _ Gerenciar Imóveis-Calculadora.html` — layout da calculadora
- `Referência original _ Listar Imóveis.html` — lista de imóveis
- `Referência original _ Ver Imóvel.html` — detalhe do imóvel
- `Referência original _ Gestão Financeira.html` — painel financeiro
- `Referência original _ Novo Lançamento.html` — form de lançamento
- `novo lançmento.png` — screenshot do form de novo lançamento
- `tela operações finalizadas.png` — screenshot do dashboard financeiro

---

## Notas de desenvolvimento

**settings ativo localmente:** `config.settings.development` (manage.py default)
**settings ativo no Railway:** `config.settings.production` (via variável `DJANGO_SETTINGS_MODULE`)

**Filtros de template disponíveis** (`{% load leilao_tags %}`):
- `{{ valor|brl }}` — formata em R$ com casas decimais
- `{{ valor|brl_short }}` — formata abreviado (R$ 1,5M, R$ 300 mil)
- `{{ valor|pct }}` — formata percentual (12,34%)
- `{{ dicionario|dict_get:chave }}` — acessa dict por variável de chave (necessário para `tg[m]`)
