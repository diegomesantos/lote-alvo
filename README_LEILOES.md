# 🏘️ Explorador de Leilões da Caixa — Quick Start

**Status**: ✅ Pronto para uso | **Dados**: 51 imóveis teste | **Apify**: Aguardando Actor ID

---

## 🚀 Acesso Rápido

| O que | URL | Login Requerido |
|------|-----|-----------------|
| **Explorador** | http://localhost:8000/leiloes/ | ✅ Sim |
| **Admin** | http://localhost:8000/admin/leiloes/ | ✅ Staff |
| **Sincronizar** | POST http://localhost:8000/leiloes/sync/ | ✅ Staff |

---

## 🎯 Features Principais

### 1. **Filtros Avançados**
```
🔍 Buscar por endereço ou cidade
🔘 Estados (multiseleção com modal)
🏙️ Cidades (multiseleção com modal)
🏢 Tipos (apto, casa, sala, lote, galpão)
💰 Valor (range min/max)
🎯 Desconto (faixas percentuais)
💳 Formas pagamento (checkbox)
📊 Ordenação (recentes, valor, desconto)
```

### 2. **Grid Responsivo**
- **Desktop (3 colunas)**: Até 12 cards/página
- **Tablet (2 colunas)**: Layout ajustado
- **Mobile (1 coluna)**: Full width

### 3. **Cards Informativos**
```
┌─────────────────────┐
│ 📸 Foto             │
├─────────────────────┤
│ Endereço (2 linhas) │
│ Tipo • Área • Qtos  │
├─────────────────────┤
│ Avaliação: R$ 350k  │
│ Desconto: -20% 🟢   │
│ Lance: R$ 280k      │
│ Valor/m²: R$ 2.800  │
├─────────────────────┤
│ 💳 Financiamento    │
│ 🏢 FGTS             │
├─────────────────────┤
│ 📅 10/06/2026       │
│ ⚠️ IPTU em atraso    │
├─────────────────────┤
│ [📄] [📊] [🔗]      │
└─────────────────────┘
```

### 4. **Integração com Calculadora**
Clica "📊 Simular" → Abre calculadora com dados pré-preenchidos

---

## 💾 Dados Teste

**51 imóveis** com variação realista:
- 🏠 Apartamentos, casas, salas, lotes, galpões
- 📍 Estados: SP, RJ, MG, BA, RS, PR
- 💰 Valores: R$ 100k a R$ 1.000k
- 📊 Descontos: 5% a 35%
- 💳 Formas pagamento variadas
- ⚠️ Com pendências simuladas

---

## ⚙️ Sincronização

### Modo Teste (Funcionando Agora)
```bash
python3 manage.py sincronizar_caixa --estado SP
```
✅ Cria 3 imóveis simulados por estado

### Modo Apify (Aguardando Configuração)
```bash
# Quando Actor ID for configurado:
python3 manage.py sincronizar_caixa --todos
```
✅ Sincroniza dados reais da Caixa para todos os estados

---

## 🔧 Comandos Úteis

```bash
# Sincronizar estado específico
python3 manage.py sincronizar_caixa --estado SP

# Sincronizar todos os estados
python3 manage.py sincronizar_caixa --todos

# Repovoar dados de teste
python3 manage.py populate_test_data --count 45

# Django shell
python3 manage.py shell
>>> from apps.leiloes.models import ImovelCaixa
>>> ImovelCaixa.objects.count()  # Total de imóveis
>>> ImovelCaixa.objects.filter(estado='SP').count()  # Por estado
```

---

## 📋 Filtros Exemplo

**URL com filtros aplicados:**
```
/leiloes/?q=Paulista&estados=SP&cidades=São Paulo&tipos=apto&valor_min=200000&valor_max=500000&desconto=20-30&financiamento=on
```

**Resultado:**
- Busca por "Paulista" no endereço
- Apenas em São Paulo, SP
- Apenas apartamentos
- Valor entre R$ 200k e R$ 500k
- Desconto entre 20-30%
- Que aceitam financiamento

---

## 🎨 Customizações

### Mudar quantidade de cards/página
Edite `apps/leiloes/views.py`:
```python
paginator = Paginator(queryset, 12)  # ← Mude para 20, 30, etc
```

### Adicionar novo filtro
1. Adicione campo em `ImovelCaixa.objects.filter()`
2. Adicione input no template `explorador.html`
3. Adicione `@require_http_methods` se necessário

### Customizar design dos cards
Edite `templates/leiloes/explorador.html` seção `<!-- Card -->`

---

## 🚨 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Nenhum imóvel encontrado" | Execute `populate_test_data` |
| Filtros não funcionam | Verifique nome dos parâmetros GET |
| Imagem não carrega | URL foto_url está vazia (teste usa placeholder) |
| Erro ao simular | Verifique se calculadora está funcionando |
| Sincronização trava | Aumentar timeout em `requests.post(timeout=60)` |

---

## 📊 Próximos Passos

### Para você (1 ação):
1. **Encontre o Actor ID da Caixa em Apify**
   - Acesse: https://apify.com/search?q=caixa
   - Copie o ID (formato: `username/actor-name`)
   - Compartilhe comigo

### O sistema irá (automático):
2. Atualizar `APIFY_ACTOR_ID`
3. Sincronizar dados reais
4. Rodar automático a cada 6h (Celery)
5. Mostrar leilões atualizados no explorador

---

## 📞 Suporte

**Documentação completa:**
- [IMPLEMENTACAO_COMPLETA.md](IMPLEMENTACAO_COMPLETA.md) - Visão geral
- [EXPLORADOR_LEILOES_DESIGN.md](EXPLORADOR_LEILOES_DESIGN.md) - Design/arquitetura
- [APIFY_SETUP.md](APIFY_SETUP.md) - Configuração Apify
- [EXPLORADOR_STATUS.md](EXPLORADOR_STATUS.md) - Status detalhado

---

**Implementado por**: Claude Code  
**Data**: 2026-06-03  
**Versão**: 1.0 (MVP)  
**Próxima**: 1.1 (Apify integrado)

🚀 **Pronto para usar! Vá para `/leiloes/` e explore!**
