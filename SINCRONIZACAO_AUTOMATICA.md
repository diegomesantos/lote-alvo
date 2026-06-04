# 🔄 Sincronização Automática de Leilões

**Status**: ✅ Configurado | **Frequência**: A cada 6 horas | **Custo**: Gratuito

---

## ❓ Você Precisa Executar o Comando Manualmente?

### ✅ **NÃO!** O sistema sincroniza **AUTOMATICAMENTE**

---

## 🚀 Como Funciona

### **Opção 1: Automático com Celery (Recomendado)** ⭐

O sistema sincroniza **automaticamente** a cada 6 horas:

```
00:00 → Sincronizar
06:00 → Sincronizar
12:00 → Sincronizar
18:00 → Sincronizar
```

**Para ativar:**

```bash
# Terminal 1: Inicie o worker do Celery
celery -A config worker --loglevel=info

# Terminal 2: Inicie o scheduler (beat)
celery -A config beat --loglevel=info

# Terminal 3: Seu Django normalmente
python3 manage.py runserver
```

✅ Pronto! Sistema sincroniza automaticamente a cada 6h

---

### **Opção 2: Sincronizar Manualmente (Se Quiser)** 

Se você quiser sincronizar **agora** (sem esperar 6h):

```bash
# Via comando CLI
python3 manage.py sincronizar_caixa --todos

# Via Python shell
python3 manage.py shell
>>> from apps.leiloes.views import sincronizar_imoveis_caixa
>>> sincronizar_imoveis_caixa('SP')
```

---

## 📊 O Que Sincroniza

### **Automático (Celery)**
- ✅ Todos os 10 estados principais
- ✅ A cada 6 horas
- ✅ Sem intervenção do usuário
- ✅ Logs detalhados

### **Manual (CLI)**
- ✅ Estado específico ou todos
- ✅ Quando você quiser
- ✅ Útil para testes

---

## ⚙️ Configuração

### **Arquivo**: `config/celery.py`

```python
app.conf.beat_schedule = {
    'sincronizar-leiloes-caixa-cada-6h': {
        'task': 'apps.leiloes.tasks.sincronizar_leiloes_caixa_task',
        'schedule': crontab(minute=0, hour='*/6'),  # A cada 6 horas
    },
}
```

### **Personalizar Frequência**

Se quiser mudar para **a cada 2 horas**:
```python
'schedule': crontab(minute=0, hour='*/2'),
```

Se quiser mudar para **diariamente às 9 da manhã**:
```python
'schedule': crontab(minute=0, hour=9),
```

Se quiser mudar para **cada hora**:
```python
'schedule': crontab(minute=0),
```

---

## 🔧 Instalação de Dependências

Celery precisa de um broker (Redis ou RabbitMQ). Para desenvolvimento, use in-memory:

```bash
# Instalar Celery
pip install celery

# Ou com Redis (produção)
pip install celery redis
```

### **Versão Simplificada (Sem Dependências Externas)**

Se não quiser instalar Celery, use **APScheduler**:

```bash
pip install apscheduler django-apscheduler
```

---

## 📝 Task (Celery)

### **Arquivo**: `apps/leiloes/tasks.py`

```python
@shared_task
def sincronizar_leiloes_caixa_task():
    """
    Task Celery para sincronizar leilões periodicamente
    Executar a cada 6 horas
    """
    estados = ['SP', 'RJ', 'MG', 'BA', 'RS', 'PR', 'PE', 'CE', 'PA', 'SC']
    
    total_criados = 0
    total_atualizados = 0
    todos_erros = []

    for estado in estados:
        criados, atualizados, erros = sincronizar_imoveis_caixa(estado)
        total_criados += criados
        total_atualizados += atualizados
        todos_erros.extend(erros)

    return {
        'criados': total_criados,
        'atualizados': total_atualizados,
        'erros': len(todos_erros)
    }
```

---

## 📊 Monitorar Sincronizações

### **Via Django Admin**

```
http://localhost:8000/admin/django_celery_beat/
```

Você verá:
- ✅ Próxima execução agendada
- ✅ Última execução
- ✅ Resultado (sucesso/erro)

### **Via CLI**

```bash
# Ver tasks ativas
celery -A config inspect active

# Ver stats do worker
celery -A config inspect stats

# Ver tasks agendadas (beat)
celery -A config inspect scheduled
```

---

## 🚨 Troubleshooting

### **Celery não está sincronizando**

**Problema**: Tasks não estão rodando automaticamente

**Solução**:
1. Verifique se o `beat` está rodando (Terminal 2)
2. Verifique se o `worker` está rodando (Terminal 1)
3. Verifique os logs para erros

### **Erro: "No module named 'celery'"**

```bash
pip install celery
```

### **Quer sincronizar agora sem esperar 6h?**

```bash
python3 manage.py syncdb  # Cria tabelas do Celery
celery -A config call apps.leiloes.tasks.sincronizar_leiloes_caixa_task
```

---

## 🎯 Resumo

| Aspecto | Status |
|--------|--------|
| **Manual?** | ❌ Não precisa |
| **Automático?** | ✅ Sim, a cada 6h |
| **Custo?** | ✅ Gratuito |
| **Configuração?** | ✅ Pronta |
| **Fácil de usar?** | ✅ Muito |

---

## 📋 Checklist de Setup

- [ ] Instalar Celery: `pip install celery`
- [ ] Inicia Worker: `celery -A config worker --loglevel=info`
- [ ] Inicia Beat: `celery -A config beat --loglevel=info`
- [ ] Inicia Django: `python3 manage.py runserver`
- [ ] Verifique sincronização em 6 horas ⏰

---

## ✨ Depois

O sistema sincroniza **automaticamente**:
- 📊 Dados sempre atualizados
- ⚡ Zero esforço do usuário
- 🎯 Sistema sempre com informações recentes
- 💾 Histórico completo no banco

---

**Tudo automático! Você não precisa fazer nada! 🚀**
