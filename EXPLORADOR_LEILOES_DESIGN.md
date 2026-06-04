# Explorador de Leilões da Caixa — Design & Implementação
**Versão**: 2.0 | **Data**: 2026-06-03 | **Status**: Pronto para Implementação

---

## 📊 Análise Comparativa dos Modelos

### Modelo 1: arrematadorcaixa.com.br
**Pontos Fortes**:
- ✅ Filtros multiseleção pesquisáveis (tags/pills)
- ✅ Busca por endereço em tempo real
- ✅ Cards com informações essenciais (valor, desconto, ROI)
- ✅ Botão "Ver card no módulo de gestão" → integração com simulação
- ✅ Layout responsivo com grid de cards
- ✅ Informações de formas de pagamento (FGTS, financiamento, consórcio)
- ✅ Link direto para o site/edital do leilão
- ✅ Fotos do imóvel
- ✅ Dados jurídicos e pendências

### Modelo 2: vivareal.com.br
**Pontos Fortes**:
- ✅ Busca avançada com múltiplos critérios
- ✅ Filtros em sidebar (melhor UX para filtros complexos)
- ✅ Exibição de preço/m² para comparação
- ✅ Informações de ocupação do imóvel
- ✅ Detalhes de dividas e responsabilidades
- ✅ Histórico de preços/acompanhamento
- ✅ Status jurídico completo (penhoras, ônus, etc)
- ✅ Documentos disponíveis (matrícula, edital)
- ✅ Detalhes de proprietário e finalizações

---

## 🎯 Nossa Estratégia: "Melhor dos Dois"

Vamos combinar:
1. **Layout do arrematador** (sidebar + cards principais)
2. **Filtros avançados do VivaReal** (multiseleção, pesquisa)
3. **Dados disponíveis da API Apify** (o que conseguimos)
4. **Integração com Simulação** (nossa diferença competitiva)

---

## 🏗️ Arquitetura da Solução

```
┌────────────────────────────────────────────────────┐
│  EXPLORADOR DE LEILÕES DA CAIXA                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │    SIDEBAR       │  │    ÁREA PRINCIPAL    │  │
│  │    (Filtros)     │  │                      │  │
│  ├──────────────────┤  ├──────────────────────┤  │
│  │ 🔍 Busca Global  │  │  📋 Resultados       │  │
│  │                  │  │  ├─ Grid de Cards   │  │
│  │ FILTROS:         │  │  ├─ Detalhes Rápido │  │
│  │ • Estado (chips) │  │  └─ Botões de Ação  │  │
│  │ • Cidade (chips) │  │                      │  │
│  │ • Tipo (multi)   │  │  PAGINAÇÃO           │  │
│  │ • Valor (range)  │  │                      │  │
│  │ • Desconto       │  │                      │  │
│  │ • Financiamento  │  │                      │  │
│  │                  │  │                      │  │
│  │ [Aplicar Filtros]│  │                      │  │
│  │ [Limpar Tudo]    │  │                      │  │
│  └──────────────────┘  └──────────────────────┘  │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 💾 Dados Disponíveis na API Apify

Com base na documentação Apify, teremos acesso a:

```json
{
  // Identificação
  "imovelId": "12345",
  "endereco": "Rua das Flores, 123, Apto 401",
  "cidade": "São Paulo",
  "estado": "SP",
  "cep": "01234-567",
  
  // Características
  "tipo": "Apartamento",  // Apartamento, Casa, Sala, Lote, Galpão
  "quartos": 3,
  "area_util": 125,        // em m²
  
  // Valores & Desconto
  "valor_avaliacao": 350000,
  "percentual_desconto": 20,
  "valor_minimo_lance": 280000,
  "valor_final": 280000,
  
  // Leilão
  "data_leilao": "2026-06-10",
  "hora_leilao": "14:00",
  "tipo_leilao": "Extrajudicial",  // Extrajudicial, Judicial
  
  // Pagamento
  "formas_pagamento": {
    "a_vista": true,
    "fgts": false,
    "financiamento": true,
    "consorcio": false,
    "parcelado": true
  },
  
  // Documentação
  "edital_url": "https://...",
  "matricula_url": "https://...",
  "foto_url": "https://...",
  
  // Status
  "ocupado": true,
  "pendencias": ["IPTU em atraso", "Condomínio"],
  "possui_penhora": true,
  
  // Metadata
  "sincronizado_em": "2026-06-03T10:30:00Z"
}
```

---

## 🎨 Design da Interface

### 1. Página Principal: `/leiloes/`

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 LoteAlvo > 🔍 Explorador de Leilões da Caixa        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────┐ ┌────────────────────────────────────┐ │
│ │  FILTROS         │ │  RESULTADOS (2.847 imóveis)        │ │
│ ├──────────────────┤ ├────────────────────────────────────┤ │
│ │                  │ │                                    │ │
│ │ 🔍 Buscar...     │ │ ┌──────────────────────────────┐  │ │
│ │                  │ │ │ 📸 Foto                      │  │ │
│ │ 🔘 ESTADO        │ │ │                              │  │ │
│ │ [SP] [RJ] [MG]   │ │ │ ED MARIEVE                   │  │ │
│ │ [BA] [RS] [PR]   │ │ │ Apto 401 | 125 m² | 3 Qtos  │  │ │
│ │ [+12 mais...]    │ │ │ São Paulo, SP                │  │ │
│ │                  │ │ │                              │  │ │
│ │ 🏙️ CIDADE        │ │ │ Avaliação: R$ 350.000       │  │ │
│ │ [São Paulo] [x]  │ │ │ Desconto: -20% 🟢           │  │ │
│ │ [Campinas] [x]   │ │ │ Lance mín: R$ 280.000       │  │ │
│ │                  │ │ │                              │  │ │
│ │ 🏢 TIPO          │ │ │ 💰 Financiamento: ✓ FGTS ✓  │  │ │
│ │ ☑ Apartamento    │ │ │ 📅 Leilão: 10/06/2026       │  │ │
│ │ ☐ Casa           │ │ │                              │  │ │
│ │ ☐ Sala           │ │ │ [📄 Ver Edital] [📊 Simular] │  │ │
│ │ ☐ Lote           │ │ │ [🔗 Ir p/ Caixa]             │  │ │
│ │                  │ │ └──────────────────────────────┘  │ │
│ │ 💰 VALOR         │ │                                    │ │
│ │ Min: R$ [_____]  │ │ [Próxima página ➜]                │ │
│ │ Max: R$ [_____]  │ │                                    │ │
│ │                  │ │                                    │ │
│ │ 🎯 DESCONTO      │ │                                    │ │
│ │ [0-10%] [10-20%] │ │                                    │ │
│ │ [20-30%] [30%+]  │ │                                    │ │
│ │                  │ │                                    │ │
│ │ [Aplicar Filtros]│ │                                    │ │
│ │ [Limpar Tudo]    │ │                                    │ │
│ │                  │ │                                    │ │
│ └──────────────────┘ └────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Card do Imóvel (Detalhe Rápido)

```
┌────────────────────────────────────────┐
│ 📸 [Foto do imóvel - 100% width]      │
│ [ED MARIEVE - 3 quartos - 125 m²]    │
├────────────────────────────────────────┤
│ Rua Ladeira do Cacau, 11 - SP        │
│                                        │
│ 💰 Valores:                            │
│ Avaliação    R$ 350.000              │
│ -20% Desconto                         │
│ Lance mín.   R$ 280.000 ✨ MELHOR    │
│                                        │
│ 📊 Índices:                            │
│ Valor/m² R$ 2.800 (acima da média)   │
│                                        │
│ ✓ Financiamento ✓ FGTS ✗ Consórcio   │
│ 📅 Leilão 10/06/2026 às 14:00        │
│                                        │
│ ⚠️ Ocupado | Pendências               │
│                                        │
│ [📄 Edital] [📊 Simular] [🔗 Caixa]  │
└────────────────────────────────────────┘
```

### 3. Filtros com Multiseleção

**ESTADO**:
```
[SP ✓] [RJ ✓] [MG ✓] [BA] [RS] [PR] [+12 mais...]
```
- Busca pesquisável: Ao clicar em "Adicionar Estado" → Modal/Dropdown com busca

**CIDADE**:
```
[São Paulo ✓] [x]  [Rio de Janeiro ✓] [x]  [+Adicionar...]
```
- Autocomplete baseado no estado selecionado
- Pills/chips removíveis

**TIPO**:
```
☑ Apartamento (1.234)
☐ Casa (567)
☐ Sala (89)
☐ Lote (12)
```

---

## 🔧 Implementação Backend

### 1. Model ImovelCaixa

```python
# apps/leiloes/models.py
from django.db import models

class ImovelCaixa(models.Model):
    TIPO_CHOICES = [
        ('apto', 'Apartamento'),
        ('casa', 'Casa'),
        ('sala', 'Sala Comercial'),
        ('lote', 'Lote'),
        ('galpao', 'Galpão'),
    ]
    
    TIPO_LEILAO_CHOICES = [
        ('extra', 'Extrajudicial'),
        ('judicial', 'Judicial'),
    ]
    
    # Identificação
    imovel_id_caixa = models.CharField(unique=True, max_length=50)
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=10, null=True, blank=True)
    
    # Características
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    quartos = models.IntegerField(null=True, blank=True)
    area_util = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # Valores
    valor_avaliacao = models.DecimalField(max_digits=12, decimal_places=2)
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2)
    valor_minimo_lance = models.DecimalField(max_digits=12, decimal_places=2)
    valor_final = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    
    # Leilão
    data_leilao = models.DateField()
    hora_leilao = models.TimeField(null=True)
    tipo_leilao = models.CharField(max_length=20, choices=TIPO_LEILAO_CHOICES)
    
    # Formas de Pagamento (usando JSONField)
    formas_pagamento = models.JSONField(default=dict)  # {"a_vista": true, "fgts": false, ...}
    
    # URLs
    edital_url = models.URLField(null=True, blank=True)
    matricula_url = models.URLField(null=True, blank=True)
    foto_url = models.URLField(null=True, blank=True)
    
    # Status
    ocupado = models.BooleanField(default=True)
    pendencias = models.JSONField(default=list)  # ["IPTU em atraso", "Condomínio"]
    possui_penhora = models.BooleanField(default=False)
    
    # Metadata
    sincronizado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data_leilao', '-valor_avaliacao']
        indexes = [
            models.Index(fields=['estado', 'cidade']),
            models.Index(fields=['tipo']),
            models.Index(fields=['data_leilao']),
        ]
    
    def __str__(self):
        return f"{self.endereco} - {self.cidade}/{self.estado}"
    
    @property
    def valor_desconto_reais(self):
        return self.valor_avaliacao - self.valor_minimo_lance
    
    @property
    def pode_financiar(self):
        return self.formas_pagamento.get('financiamento', False)
    
    @property
    def pode_fgts(self):
        return self.formas_pagamento.get('fgts', False)
```

### 2. View de Listagem com Filtros

```python
# apps/leiloes/views.py
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator
from .models import ImovelCaixa

def explorador_leiloes(request):
    """
    Explorador de leilões com filtros avançados
    """
    queryset = ImovelCaixa.objects.all()
    
    # 🔍 Busca por endereço/cidade
    busca = request.GET.get('q', '').strip()
    if busca:
        queryset = queryset.filter(
            Q(endereco__icontains=busca) |
            Q(cidade__icontains=busca)
        )
    
    # 🔘 Filtro por estado (multiseleção)
    estados = request.GET.getlist('estados')
    if estados:
        queryset = queryset.filter(estado__in=estados)
    
    # 🏙️ Filtro por cidade (multiseleção)
    cidades = request.GET.getlist('cidades')
    if cidades:
        queryset = queryset.filter(cidade__in=cidades)
    
    # 🏢 Filtro por tipo (multiseleção)
    tipos = request.GET.getlist('tipos')
    if tipos:
        queryset = queryset.filter(tipo__in=tipos)
    
    # 💰 Filtro por valor (range)
    valor_min = request.GET.get('valor_min')
    valor_max = request.GET.get('valor_max')
    if valor_min:
        queryset = queryset.filter(valor_minimo_lance__gte=valor_min)
    if valor_max:
        queryset = queryset.filter(valor_minimo_lance__lte=valor_max)
    
    # 🎯 Filtro por desconto
    desconto_min = request.GET.get('desconto_min')
    if desconto_min:
        queryset = queryset.filter(percentual_desconto__gte=desconto_min)
    
    # 💳 Filtro por formas de pagamento
    permite_financiamento = request.GET.get('financiamento') == 'true'
    permite_fgts = request.GET.get('fgts') == 'true'
    
    if permite_financiamento:
        queryset = queryset.filter(formas_pagamento__financiamento=True)
    if permite_fgts:
        queryset = queryset.filter(formas_pagamento__fgts=True)
    
    # 📊 Ordenação
    ordenar_por = request.GET.get('ordenar', '-data_leilao')
    queryset = queryset.order_by(ordenar_por)
    
    # Paginação
    paginator = Paginator(queryset, 12)  # 12 cards por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Estados e cidades disponíveis (para dropdowns)
    estados_disponiveis = ImovelCaixa.objects.values_list('estado', flat=True).distinct().order_by('estado')
    cidades_disponiveis = ImovelCaixa.objects.values_list('cidade', flat=True).distinct().order_by('cidade')
    
    context = {
        'page_obj': page_obj,
        'total': queryset.count(),
        'estados_disponiveis': estados_disponiveis,
        'cidades_disponiveis': cidades_disponiveis,
        'filtros_ativos': {
            'q': busca,
            'estados': estados,
            'cidades': cidades,
            'tipos': tipos,
        }
    }
    
    return render(request, 'leiloes/explorador.html', context)
```

### 3. API para AJAX (Multiseleção)

```python
# apps/leiloes/views.py
from django.http import JsonResponse

def api_cidades_por_estado(request):
    """API para preencher cidades quando estado é selecionado"""
    estado = request.GET.get('estado')
    
    cidades = ImovelCaixa.objects\
        .filter(estado=estado)\
        .values_list('cidade', flat=True)\
        .distinct()\
        .order_by('cidade')
    
    return JsonResponse({
        'cidades': list(cidades)
    })
```

### 4. URLs

```python
# apps/leiloes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.explorador_leiloes, name='explorador_leiloes'),
    path('api/cidades/', views.api_cidades_por_estado, name='api_cidades'),
]
```

---

## 🎨 Template Frontend

### `templates/leiloes/explorador.html`

```html
{% extends "base.html" %}
{% load static leilao_tags %}

{% block title %}Explorador de Leilões da Caixa — LoteAlvo{% endblock %}
{% block page_title %}🏠 Explorador de Leilões da Caixa{% endblock %}
{% block page_subtitle %}Encontre oportunidades de investimento em imóveis do Brasil todo{% endblock %}

{% block content %}
<div class="flex gap-6" x-data="explorador_leiloes()">
  
  <!-- SIDEBAR: FILTROS -->
  <aside class="w-80 flex-shrink-0">
    <div class="bg-white rounded-lg border border-gray-200 p-6 sticky top-24">
      <form id="filtros-form" method="get" @submit.prevent="aplicar_filtros">
        
        <!-- Busca Global -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-2">🔍 Buscar Imóvel</label>
          <input 
            type="text" 
            name="q" 
            placeholder="Endereço, cidade..."
            value="{{ filtros_ativos.q }}"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-400">
        </div>
        
        <!-- Filtro: Estado -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">🔘 Estado</label>
          <div id="estados-container" class="flex flex-wrap gap-2 mb-3">
            <!-- Pills inseridas via JS -->
          </div>
          <button 
            type="button"
            @click="abrir_modal_estados()"
            class="w-full px-3 py-2 text-sm border border-teal-300 text-teal-600 rounded-lg hover:bg-teal-50">
            + Adicionar Estado
          </button>
        </div>
        
        <!-- Filtro: Cidade -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">🏙️ Cidade</label>
          <div id="cidades-container" class="flex flex-wrap gap-2 mb-3">
            <!-- Pills inseridas via JS -->
          </div>
          <button 
            type="button"
            @click="abrir_modal_cidades()"
            class="w-full px-3 py-2 text-sm border border-teal-300 text-teal-600 rounded-lg hover:bg-teal-50">
            + Adicionar Cidade
          </button>
        </div>
        
        <!-- Filtro: Tipo de Imóvel -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">🏢 Tipo</label>
          <div class="space-y-2">
            <label class="flex items-center gap-2">
              <input type="checkbox" name="tipos" value="apto" class="rounded">
              <span class="text-sm">Apartamento</span>
              <span class="text-xs text-gray-500">(1.234)</span>
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" name="tipos" value="casa" class="rounded">
              <span class="text-sm">Casa</span>
              <span class="text-xs text-gray-500">(567)</span>
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" name="tipos" value="sala" class="rounded">
              <span class="text-sm">Sala Comercial</span>
              <span class="text-xs text-gray-500">(89)</span>
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" name="tipos" value="lote" class="rounded">
              <span class="text-sm">Lote</span>
              <span class="text-xs text-gray-500">(12)</span>
            </label>
          </div>
        </div>
        
        <!-- Filtro: Valor -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">💰 Valor</label>
          <div class="space-y-2">
            <div>
              <label class="text-xs text-gray-600">Mín. R$</label>
              <input 
                type="number" 
                name="valor_min" 
                placeholder="100.000"
                class="w-full px-3 py-2 border border-gray-300 rounded text-sm">
            </div>
            <div>
              <label class="text-xs text-gray-600">Máx. R$</label>
              <input 
                type="number" 
                name="valor_max" 
                placeholder="1.000.000"
                class="w-full px-3 py-2 border border-gray-300 rounded text-sm">
            </div>
          </div>
        </div>
        
        <!-- Filtro: Desconto -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">🎯 Desconto</label>
          <div class="flex gap-2">
            <label class="flex-1 text-center">
              <input type="radio" name="desconto" value="0-10">
              <span class="text-xs">0-10%</span>
            </label>
            <label class="flex-1 text-center">
              <input type="radio" name="desconto" value="10-20">
              <span class="text-xs">10-20%</span>
            </label>
            <label class="flex-1 text-center">
              <input type="radio" name="desconto" value="20-30">
              <span class="text-xs">20-30%</span>
            </label>
            <label class="flex-1 text-center">
              <input type="radio" name="desconto" value="30+">
              <span class="text-xs">30%+</span>
            </label>
          </div>
        </div>
        
        <!-- Filtro: Formas de Pagamento -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-900 mb-3">💳 Pagamento</label>
          <div class="space-y-2">
            <label class="flex items-center gap-2">
              <input type="checkbox" name="financiamento" value="true">
              <span class="text-sm">Financiamento</span>
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" name="fgts" value="true">
              <span class="text-sm">FGTS</span>
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" name="consorcio" value="true">
              <span class="text-sm">Consórcio</span>
            </label>
          </div>
        </div>
        
        <!-- Botões -->
        <div class="flex gap-2">
          <button 
            type="submit"
            class="flex-1 px-4 py-2.5 bg-teal-500 hover:bg-teal-600 text-white rounded-lg font-bold text-sm">
            Aplicar Filtros
          </button>
          <button 
            type="button"
            @click="limpar_filtros()"
            class="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium text-sm">
            Limpar
          </button>
        </div>
      </form>
    </div>
  </aside>
  
  <!-- ÁREA PRINCIPAL: RESULTADOS -->
  <main class="flex-1">
    <div class="bg-white rounded-lg border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Resultados</h2>
          <p class="text-sm text-gray-600">{{ total }} imóveis encontrados</p>
        </div>
        <select name="ordenar" onchange="this.form.submit()" class="px-3 py-2 border border-gray-300 rounded text-sm">
          <option value="-data_leilao">Mais Recentes</option>
          <option value="valor_minimo_lance">Menor Valor</option>
          <option value="-valor_minimo_lance">Maior Valor</option>
          <option value="-percentual_desconto">Maior Desconto</option>
        </select>
      </div>
      
      <!-- Grid de Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {% for imovel in page_obj %}
          <div class="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
            <!-- Foto -->
            {% if imovel.foto_url %}
              <div class="h-40 bg-gray-200 overflow-hidden">
                <img src="{{ imovel.foto_url }}" alt="{{ imovel.endereco }}" class="w-full h-full object-cover">
              </div>
            {% else %}
              <div class="h-40 bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
                <span class="text-4xl">🏠</span>
              </div>
            {% endif %}
            
            <!-- Conteúdo do Card -->
            <div class="p-4">
              <!-- Título e Tipo -->
              <h3 class="font-bold text-sm text-gray-900 line-clamp-2 mb-1">{{ imovel.endereco }}</h3>
              <div class="flex items-center gap-2 text-xs text-gray-600 mb-3">
                <span>{{ imovel.get_tipo_display }}</span>
                {% if imovel.area_util %}
                  <span>•</span>
                  <span>{{ imovel.area_util|floatformat:0 }} m²</span>
                {% endif %}
                {% if imovel.quartos %}
                  <span>•</span>
                  <span>{{ imovel.quartos }}q</span>
                {% endif %}
              </div>
              
              <!-- Valores -->
              <div class="mb-3 pb-3 border-t border-gray-100">
                <div class="text-xs text-gray-600 mb-1">Avaliação</div>
                <div class="text-lg font-bold text-gray-900">{{ imovel.valor_avaliacao|brl }}</div>
                <div class="text-sm text-green-600 font-bold">
                  -{{ imovel.percentual_desconto|floatformat:0 }}% 🟢
                </div>
                <div class="text-xs text-gray-600 mt-2">Lance mín.</div>
                <div class="font-bold text-teal-600">{{ imovel.valor_minimo_lance|brl }}</div>
              </div>
              
              <!-- Formas de Pagamento -->
              <div class="flex flex-wrap gap-1 mb-3">
                {% if imovel.pode_financiar %}
                  <span class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">💳 Financiamento</span>
                {% endif %}
                {% if imovel.pode_fgts %}
                  <span class="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">🏢 FGTS</span>
                {% endif %}
              </div>
              
              <!-- Data do Leilão -->
              <div class="text-xs text-gray-600 mb-3">
                📅 {{ imovel.data_leilao|date:"d/m/Y" }}
              </div>
              
              <!-- Pendências/Avisos -->
              {% if imovel.pendencias %}
                <div class="text-xs text-red-600 mb-3 bg-red-50 p-2 rounded">
                  ⚠️ {{ imovel.pendencias|join:", " }}
                </div>
              {% endif %}
              
              <!-- Botões de Ação -->
              <div class="flex gap-2">
                <a 
                  href="{{ imovel.edital_url }}" 
                  target="_blank"
                  class="flex-1 px-2 py-1.5 text-xs border border-teal-300 text-teal-600 rounded hover:bg-teal-50 font-medium text-center">
                  📄 Edital
                </a>
                <button 
                  @click="simular_imovel({{ imovel.imovel_id_caixa }})"
                  class="flex-1 px-2 py-1.5 text-xs bg-teal-500 text-white rounded hover:bg-teal-600 font-medium">
                  📊 Simular
                </button>
                <a 
                  href="https://www.caixa.gov.br/imoveiscaixa"
                  target="_blank"
                  title="Ver no site da Caixa"
                  class="px-2 py-1.5 text-xs border border-gray-300 text-gray-600 rounded hover:bg-gray-50">
                  🔗
                </a>
              </div>
            </div>
          </div>
        {% empty %}
          <div class="col-span-3 text-center py-12">
            <p class="text-gray-600 font-medium">Nenhum imóvel encontrado com esses filtros.</p>
            <p class="text-sm text-gray-500 mt-2">Tente ajustar os critérios de busca.</p>
          </div>
        {% endfor %}
      </div>
      
      <!-- Paginação -->
      {% if page_obj.has_other_pages %}
        <div class="flex items-center justify-center gap-2 pt-6 border-t border-gray-200">
          {% if page_obj.has_previous %}
            <a href="?page=1" class="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">⬅️ Primeira</a>
            <a href="?page={{ page_obj.previous_page_number }}" class="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Anterior</a>
          {% endif %}
          
          <span class="text-sm text-gray-600">
            Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
          </span>
          
          {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}" class="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Próxima</a>
            <a href="?page={{ page_obj.paginator.num_pages }}" class="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Última ➜</a>
          {% endif %}
        </div>
      {% endif %}
    </div>
  </main>
</div>

<!-- Modal: Seleção de Estados -->
<div id="modal-estados" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div class="bg-white rounded-lg p-6 w-96 max-h-96 overflow-y-auto">
    <h3 class="font-bold text-lg mb-4">Selecionar Estados</h3>
    <input 
      type="text" 
      placeholder="Buscar estado..." 
      id="busca-estados"
      class="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 text-sm">
    <div id="lista-estados" class="space-y-2"></div>
  </div>
</div>

<script>
function explorador_leiloes() {
  return {
    abrir_modal_estados() {
      document.getElementById('modal-estados').classList.remove('hidden');
    },
    abrir_modal_cidades() {
      // Similar ao de estados
    },
    aplicar_filtros() {
      document.getElementById('filtros-form').submit();
    },
    limpar_filtros() {
      window.location.href = '{% url "explorador_leiloes" %}';
    },
    simular_imovel(imovelId) {
      // Redireciona para calculadora com dados pré-preenchidos
      alert('Preparando simulação para imóvel ' + imovelId);
    }
  }
}
</script>
{% endblock %}
```

---

## 🔄 Fluxo de "Importar para Simulação"

Quando o usuário clica em **"📊 Simular"**:

1. ✅ Puxa dados do ImovelCaixa
2. ✅ Mapeia para campos da Simulação
3. ✅ Abre a Calculadora pré-preenchida
4. ✅ Usuário ajusta parâmetros
5. ✅ Simula ROI baseado em dados reais

```javascript
// JavaScript para "Simular"
function simular_imovel(imovelId) {
  // Fetch dados da Caixa
  fetch(`/leiloes/api/imovel/${imovelId}/`)
    .then(r => r.json())
    .then(data => {
      // Monta URL com parâmetros da calculadora
      const params = new URLSearchParams({
        avaliacao: data.valor_avaliacao,
        lance: data.valor_minimo_lance,
        endereco: data.endereco,
        tipo_leilao: data.tipo_leilao,
      });
      window.location.href = `/calculadora/?${params}`;
    });
}
```

---

## 📋 Checklist de Implementação

- [ ] Criar app `leiloes`
- [ ] Implementar modelo `ImovelCaixa`
- [ ] Criar migrations
- [ ] Implementar view `explorador_leiloes`
- [ ] Implementar API `api_cidades_por_estado`
- [ ] Criar template `explorador.html`
- [ ] Implementar multiseleção com modals
- [ ] Integrar com Apify (sincronização via Celery)
- [ ] Testar filtros (estado, cidade, tipo, valor, desconto)
- [ ] Implementar "Simular" → redireção à calculadora
- [ ] Deploy

---

## 🎯 Próximas Etapas

1. **Você aprova este design?** Se sim, começamos a implementação.
2. **Setup Apify**: Você cria conta e coleta o `APIFY_API_TOKEN`?
3. **Prioridade**: Qual você prefere iniciar?
   - a) Implementação do explorador
   - b) Sincronização com Apify via Celery
   - c) Integração com Calculadora

