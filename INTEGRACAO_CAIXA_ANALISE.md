# Integração de Dados de Leilões da Caixa — Análise Técnica

## 🎯 Objetivo
Integrar dados de imóveis em leilão da Caixa Econômica Federal na aplicação LoteAlvo, permitindo:
- Visualizar imóveis disponíveis em leilão
- Importar dados para simulação
- Acompanhar leilões automaticamente
- Comparar com outras fontes

---

## 📊 Opções Disponíveis de Integração

### Opção 1: Apify Caixa Leilões API ⭐ **RECOMENDADA**
**URL**: https://apify.com/brasil-scrapers/caixa-leiloes-api

#### Características
- ✅ API pronta para uso
- ✅ Dados estruturados em JSON
- ✅ Filtros por estado, cidade, modalidade
- ✅ Retorna: valor avaliação, desconto, datas, forma pagamento, PDF matrícula
- ✅ Documentação disponível

#### Precificação
- **Free Tier**: 
  - Até 10.000 créditos/mês
  - ~50 execuções/dia com dados completos
- **Paid**: A partir de $9/mês com créditos adicionais

#### Como Funciona
```
1. Criar conta em apify.com
2. Obter API token
3. Configurar parâmetros (estado, cidade)
4. Fazer requisição HTTP POST
5. Receber JSON com dados dos imóveis
```

#### Exemplo de Requisição
```bash
curl -X POST \
  https://api.apify.com/v2/acts/brasil-scrapers~caixa-leiloes-api/run-sync \
  -H "Authorization: Bearer SEU_TOKEN_APIFY" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "SP",
    "city": "SAO PAULO",
    "mode": 1
  }'
```

#### Dados Retornados
```json
{
  "imovelId": "12345",
  "endereco": "Rua das Flores, 123",
  "cidade": "São Paulo",
  "estado": "SP",
  "tipoImovel": "Apartamento",
  "avaliacao": 350000,
  "desconto": 20,
  "valorMinimoLance": 280000,
  "dataLeilao": "2026-06-10",
  "formaPagamento": "À Vista",
  "matricula_pdf_url": "https://...",
  "edital_url": "https://..."
}
```

---

### Opção 2: Web Scraping Manual
**Alternativa se Apify não atender às necessidades**

#### Características
- ⚠️ Requer manutenção contínua
- ⚠️ Pode quebrar se site mudar estrutura
- ✅ Custo zero
- ✅ Controle total

#### Ferramentas
- Selenium (Python)
- Beautiful Soup
- Scrapy

#### Desvantagens
- Site pode ter proteção anti-scraping
- Pode ser bloqueado por IP
- Precisa rodar frequentemente para atualizar dados

---

### Opção 3: Acesso Direto ao Portal da Caixa
**URL**: https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp

#### Características
- ✅ Oficialmente fornecido pela Caixa
- ✅ Atualizado regularmente
- ❌ Formato: CSV/Excel (não JSON)
- ❌ Requer parse manual
- ✅ Totalmente gratuito

#### Processo
1. Baixar arquivo CSV mensalmente
2. Fazer upload no sistema
3. Processar e importar dados
4. Armazenar em banco de dados local

---

## 🛠️ Implementação Recomendada (Opção 1 - Apify)

### Arquitetura

```
┌─────────────────────────────────────────┐
│  Apify Caixa Leilões API                │
│  (Dados atualizados em tempo real)      │
└──────────────┬──────────────────────────┘
               │ HTTP REST API
               ↓
┌─────────────────────────────────────────┐
│  apps/leiloes/                          │
│  ├── views.py (listar, importar)        │
│  ├── models.py (ImovelCaixa)            │
│  ├── urls.py                            │
│  └── tasks.py (sincronização periódica) │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Banco de Dados Local                   │
│  (Cache de imóveis da Caixa)            │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Frontend                               │
│  ├── Página de exploração de leilões    │
│  ├── Filtros (estado, cidade, tipo)     │
│  └── "Importar para simulação"          │
└─────────────────────────────────────────┘
```

### Passo 1: Setup Apify

```python
# settings.py
APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
APIFY_ACTOR_ID = 'brasil-scrapers/caixa-leiloes-api'
APIFY_API_URL = 'https://api.apify.com/v2/acts/{actor_id}/run-sync'
```

### Passo 2: Models

```python
# apps/leiloes/models.py
class ImovelCaixa(models.Model):
    # Identificação
    imovel_id = models.CharField(unique=True)
    endereco = models.CharField()
    cidade = models.CharField()
    estado = models.CharField()
    
    # Características
    tipo_imovel = models.CharField()
    area_util = models.IntegerField(null=True)
    
    # Valores
    valor_avaliacao = models.DecimalField()
    desconto_percentual = models.DecimalField()
    valor_minimo_lance = models.DecimalField()
    
    # Leilão
    data_leilao = models.DateField()
    forma_pagamento = models.CharField()
    
    # Links
    edital_url = models.URLField()
    matricula_pdf_url = models.URLField()
    
    # Metadata
    importado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
```

### Passo 3: View para Buscar

```python
# apps/leiloes/views.py
import requests
from django.conf import settings

def buscar_imoveis_caixa(estado=None, cidade=None):
    """Busca imóveis na API Apify Caixa"""
    
    url = settings.APIFY_API_URL.format(
        actor_id=settings.APIFY_ACTOR_ID
    )
    
    payload = {
        "state": estado or "SP",
        "city": cidade,
        "mode": 1
    }
    
    headers = {
        "Authorization": f"Bearer {settings.APIFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    # Processa resposta e salva no BD
    for imovel in data.get('data', []):
        ImovelCaixa.objects.update_or_create(
            imovel_id=imovel['imovelId'],
            defaults={
                'endereco': imovel['endereco'],
                'valor_avaliacao': imovel['avaliacao'],
                # ... outros campos
            }
        )
    
    return len(data.get('data', []))
```

### Passo 4: Task Assíncrona

```python
# apps/leiloes/tasks.py (Celery)
from celery import shared_task
from .views import buscar_imoveis_caixa

@shared_task
def sincronizar_leiloes_caixa():
    """Sincroniza leilões da Caixa a cada 6 horas"""
    
    estados = ['SP', 'RJ', 'MG', 'BA', 'RS', 'PR']
    
    for estado in estados:
        buscar_imoveis_caixa(estado=estado)
    
    return f"Sincronização completa para {len(estados)} estados"
```

### Passo 5: Template/Frontend

```html
<!-- templates/leiloes/explorador.html -->
<div class="max-w-7xl mx-auto">
  <h1>🏠 Explorador de Leilões da Caixa</h1>
  
  <!-- Filtros -->
  <div class="filters">
    <input type="text" placeholder="Cidade" id="cidade">
    <select id="estado">
      <option value="">Todos os estados</option>
      <option value="SP">São Paulo</option>
      <option value="RJ">Rio de Janeiro</option>
      <!-- ... -->
    </select>
    <button onclick="filtrar()">Buscar</button>
  </div>
  
  <!-- Resultados em tabela/cards -->
  <div id="resultados" class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- Cards dos imóveis -->
  </div>
</div>
```

---

## 💰 Análise de Custo

| Opção | Setup | Custo Mensal | Manutenção |
|-------|-------|-------------|-----------|
| Apify | Baixo | ~$0-9 | Mínima |
| Web Scraping | Médio | $0 | Alta |
| Portal CSV | Baixo | $0 | Média |

**Recomendação**: Apify para produção (confiável), CSV para backup

---

## ✅ Benefícios da Integração

1. **Dados atualizados**: Novos leilões em tempo real
2. **Alcance nacional**: Todos os estados do Brasil
3. **Simulação automática**: Importar direto para análise
4. **Comparação**: Ver similar properties na Caixa
5. **Inovação**: Diferenciar do concorrente

---

## 📋 Próximos Passos

1. **Criar conta Apify**: Obter API token (FREE)
2. **Testar API**: Fazer requisição teste
3. **Desenhar modelo**: Adicionar ImovelCaixa
4. **Implementar views**: Listar e filtrar
5. **Setup Celery**: Sincronização automática
6. **Criar UI**: Explorador de leilões
7. **Integração**: "Importar para simulação"

---

## 🔗 Referências

- [Apify Caixa Leilões API](https://apify.com/brasil-scrapers/caixa-leiloes-api)
- [Caixa - Download Lista Completa](https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp)
- [Portal Oficial Caixa Imóveis](https://www.caixa.gov.br/imoveiscaixa)

