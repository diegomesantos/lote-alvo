# Setup Apify para Sincronização de Leilões da Caixa

**Status**: ✅ Implementação pronta | ⏳ Aguardando configuração correta do Apify

---

## 📋 Resumo

A integração com Apify foi implementada e testada em **modo teste**. O sistema sincroniza automaticamente imóveis da Caixa Econômica Federal com os seguintes componentes:

- ✅ **Views Apify**: Faz requisições à API e processa dados
- ✅ **Management Commands**: Sincroniza via CLI
- ✅ **Celery Tasks**: Sincroniza periodicamente (6h)
- ✅ **Admin Endpoint**: POST `/leiloes/sync/` para sincronizar manualmente

---

## 🔧 Configuração do Apify

### Passo 1: Encontrar o Actor Correto

Você tem dois caminhos:

#### **Opção A: Usar um Actor Existente (Recomendado)**
1. Acesse https://apify.com/search?q=caixa
2. Procure por "Caixa Leilões" ou similar
3. Copie o **Actor ID** do formato: `username/actor-name`
4. Substitua em `config/settings/base.py`:
   ```python
   APIFY_ACTOR_ID = "seu-username/caixa-actor"  # ← aqui
   ```

#### **Opção B: Criar um Actor Personalizado**
Se não existir um actor pronto para Caixa, você pode:
1. Criar um novo Actor em https://apify.com
2. Usar Apify SDK para fazer web scraping de https://venda-imoveis.caixa.gov.br
3. Colocar o ID do novo actor em `APIFY_ACTOR_ID`

### Passo 2: Validar o Token

```bash
python3 manage.py shell
>>> from django.conf import settings
>>> from apps.leiloes.views import sincronizar_imoveis_caixa
>>> sincronizar_imoveis_caixa('SP')  # Testa com o token real
```

Se retornar erros, o actor ID ou token está errado.

### Passo 3: Sincronizar Dados Reais

Uma vez que o Apify está configurado:

```bash
# Via command line
python3 manage.py sincronizar_caixa --estado SP

# Para todos os estados principais
python3 manage.py sincronizar_caixa --todos

# Via HTTP POST (apenas staff)
curl -X POST http://localhost:8000/leiloes/sync/ \
  -d "estado=SP" \
  -H "X-CSRFToken: YOUR_TOKEN"
```

### Passo 4: Agendar Sincronização Automática (Celery)

Se você tiver Celery configurado:

```python
# Em config/celery.py adicione:
from celery.schedules import crontab

app.conf.beat_schedule = {
    'sincronizar-leiloes-caixa': {
        'task': 'apps.leiloes.tasks.sincronizar_leiloes_caixa_task',
        'schedule': crontab(hour='*/6'),  # A cada 6 horas
    },
}
```

Depois execute:
```bash
celery -A config beat --loglevel=info
celery -A config worker --loglevel=info
```

---

## 🧪 Modo Teste (Funcionando Agora)

Para testar sem dependência do Apify:

```bash
# Sincroniza com dados simulados
python3 manage.py shell
>>> from apps.leiloes.views import sincronizar_imoveis_caixa
>>> sincronizar_imoveis_caixa('SP', modo_teste=True)
```

Isso criará imóveis de teste para você testar a interface.

---

## 📊 Estrutura dos Dados

O sistema espera que a API Apify retorne um JSON com esta estrutura:

```json
{
  "data": [
    {
      "imovelId": "12345",
      "endereco": "Rua das Flores, 123, Apto 401",
      "cidade": "São Paulo",
      "estado": "SP",
      "cep": "01234-567",
      "tipo": "Apartamento",
      "quartos": 3,
      "areautilizada": 125,
      "avaliacao": 350000,
      "desconto": 20,
      "valorMinimoLance": 280000,
      "dataLeilao": "2026-06-10",
      "hora_leilao": "14:00:00",
      "tipo_leilao": "Extrajudicial",
      "aceita_a_vista": true,
      "aceita_fgts": false,
      "aceita_financiamento": true,
      "aceita_consorcio": false,
      "aceita_parcelado": true,
      "edital_url": "https://...",
      "matricula_url": "https://...",
      "foto_url": "https://...",
      "ocupado": true,
      "pendencias": ["IPTU em atraso"],
      "penhora": false
    }
  ]
}
```

O mapeamento automático no código converte nomes diferentes (ex: `areautilizada` → `area_util`).

---

## 🚨 Troubleshooting

### "Actor was not found or access denied" (404)
- ❌ Problema: Actor ID inválido ou token sem acesso
- ✅ Solução: Verifique o ID do actor em https://apify.com e o token em `.env`

### "Recebidos 0 imóveis"
- ❌ Problema: Actor está retornando dados vazios
- ✅ Solução: Verifique os parâmetros (estado deve ser 2 letras, ex: SP, RJ)

### Celery tasks não executando
- ❌ Problema: Celery não está rodando
- ✅ Solução: Inicie o worker: `celery -A config worker --loglevel=info`

### Muitos erros ao processar
- ❌ Problema: Dados da API não combinam com o mapeamento
- ✅ Solução: Ajuste o mapeamento em `sincronizar_imoveis_caixa()` conforme estrutura real da API

---

## 📝 Próximas Ações

1. **Você identifica o actor Apify correto** (ou cria um)
2. **Atualiza `APIFY_ACTOR_ID` em `config/settings/base.py`**
3. **Testa com `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 manage.py sincronizar_caixa --estado SP`**
4. **Se OK, configura Celery para sincronização automática**
5. **Pronto! Sistema funciona com dados reais**

---

## 🎯 O Sistema Suporta

- ✅ **Sincronização automática** via Celery (a cada 6h)
- ✅ **Sincronização manual** via CLI ou HTTP POST
- ✅ **Filtros avançados** no explorador
- ✅ **Integração com Calculadora** (clica "Simular")
- ✅ **Dados em tempo real** da Caixa
- ✅ **Fallback para teste** (modo_teste=True)

---

## 🔐 Segurança

- Token Apify armazenado em `.env` (não versionado)
- Endpoint POST `/leiloes/sync/` protegido com `@staff_member_required`
- Requests com timeout de 60s
- Tratamento de erros completo

---

**Próximo passo: Configure o Apify e me informe o Actor ID! 🚀**
