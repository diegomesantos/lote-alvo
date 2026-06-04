# ⏰ AUTOMAÇÃO: SCRAPER RODANDO 24/7

## 🎯 O Problema

Você quer que o scraper rode **automaticamente** a cada 6 horas, trazendo dados frescos sem você ter que fazer nada manualmente.

## ✅ Solução 1: Cron Job (Linux/Mac) - MAIS SIMPLES

### 1. Editar crontab:
```bash
crontab -e
```

### 2. Adicionar esta linha:
```bash
# Roda a cada 6 horas (00:00, 06:00, 12:00, 18:00)
0 */6 * * * cd /Users/diegogomessantos/Library/CloudStorage/OneDrive-Pessoal/Cursos/Asimov\ python/Meus\ Projetos/smart_leilao && .venv/bin/python manage.py scrape_caixa_real --todos >> /tmp/scraper.log 2>&1
```

### 3. Salvar e testar:
```bash
# Verificar se foi adicionado
crontab -l

# Ver logs
tail -f /tmp/scraper.log
```

---

## ✅ Solução 2: Celery Beat (Django) - MAIS ROBUSTO

### 1. Instalar Celery:
```bash
pip install celery redis django-celery-beat django-celery-results
```

### 2. Criar task em `apps/leiloes/tasks.py`:
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def scrape_caixa_task():
    """Task que roda o scraper a cada 6 horas"""
    call_command('scrape_caixa_real', '--todos')
    return "Scraping concluído!"
```

### 3. Configurar em `config/settings/base.py`:
```python
# Celery
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# Beat schedule
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'scrape-caixa-every-6-hours': {
        'task': 'apps.leiloes.tasks.scrape_caixa_task',
        'schedule': crontab(minute=0, hour='*/6'),  # A cada 6 horas
    },
}
```

### 4. Rodar Celery Beat:
```bash
# Terminal 1: Celery Worker
celery -A config worker --loglevel=info

# Terminal 2: Celery Beat
celery -A config beat --loglevel=info
```

---

## ✅ Solução 3: APScheduler (Mais Leve)

### 1. Instalar:
```bash
pip install apscheduler
```

### 2. Criar em `apps/leiloes/scheduler.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)

def job_scrape_caixa():
    """Roda scraper a cada 6 horas"""
    try:
        logger.info("🚀 Iniciando scraping automático...")
        call_command('scrape_caixa_real', '--todos')
        logger.info("✅ Scraping concluído!")
    except Exception as e:
        logger.error(f"❌ Erro no scraper: {e}")

def start_scheduler():
    """Inicia o scheduler"""
    if not scheduler.running:
        scheduler.add_job(
            job_scrape_caixa,
            'interval',
            hours=6,
            id='scrape_caixa_job'
        )
        scheduler.start()
        logger.info("📅 Scheduler iniciado (scraper a cada 6 horas)")

def stop_scheduler():
    """Para o scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("📅 Scheduler parado")
```

### 3. Inicializar no `apps.py`:
```python
from django.apps import AppConfig

class LeiloesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.leiloes'

    def ready(self):
        from apps.leiloes.scheduler import start_scheduler
        start_scheduler()
```

---

## 📊 Comparativo das Soluções

| Aspecto | Cron Job | Celery Beat | APScheduler |
|---------|----------|-------------|-------------|
| **Complexidade** | ⭐ Muito fácil | ⭐⭐⭐ Complexo | ⭐⭐ Médio |
| **Confiabilidade** | ⭐⭐⭐ Boa | ⭐⭐⭐⭐⭐ Excelente | ⭐⭐⭐⭐ Boa |
| **Dependências** | 0 | Redis, Celery | APScheduler |
| **Para Production** | ✅ | ✅ | ✅ |
| **Escalabilidade** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Setup rápido** | ✅ | ❌ | ✅ |
| **Ideal para** | MVP | Grande escala | Startups |

---

## 🎯 RECOMENDAÇÃO: Comece com Cron Job!

```bash
# 1. Abrir crontab
crontab -e

# 2. Adicionar esta linha (copie exato):
0 */6 * * * cd /Users/diegogomessantos/Library/CloudStorage/OneDrive-Pessoal/Cursos/Asimov\ python/Meus\ Projetos/smart_leilao && .venv/bin/python manage.py scrape_caixa_real --todos >> /tmp/scraper.log 2>&1

# 3. Salvar (Ctrl+X, Y, Enter no nano)

# 4. Verificar logs
tail -f /tmp/scraper.log
```

---

## 📋 SCHEDULE DE SCRAPING RECOMENDADO

### Opção 1: A cada 6 horas
```bash
0 */6 * * * # Roda em: 00:00, 06:00, 12:00, 18:00
```

### Opção 2: De manhã, tarde e noite
```bash
0 7,13,19 * * * # Roda em: 07:00, 13:00, 19:00
```

### Opção 3: A cada 3 horas
```bash
0 */3 * * * # Roda em: 00:00, 03:00, 06:00, 09:00, ...
```

### Opção 4: Uma vez por dia à noite
```bash
0 22 * * * # Roda em: 22:00 (10 da noite)
```

---

## 🔍 MONITORAR O SCRAPER AUTOMÁTICO

### Ver logs em tempo real:
```bash
tail -f /tmp/scraper.log
```

### Ver quando foi a última execução:
```bash
ls -lh /tmp/scraper.log
```

### Ver histórico completo:
```bash
cat /tmp/scraper.log | tail -100
```

### Grep por erros:
```bash
grep "❌" /tmp/scraper.log
```

---

## 🚨 TROUBLESHOOTING

### O scraper não está rodando?

1. **Verificar se cron está ativo:**
```bash
# Ver todos os jobs
crontab -l

# Se vazio, adicionar novamente
crontab -e
```

2. **Verificar permissões:**
```bash
ls -la /tmp/scraper.log
```

3. **Testar manualmente:**
```bash
cd /Users/diegogomessantos/Library/CloudStorage/OneDrive-Pessoal/Cursos/Asimov\ python/Meus\ Projetos/smart_leilao && .venv/bin/python manage.py scrape_caixa_real --todos
```

4. **Ver se há permissão de escrita:**
```bash
touch /tmp/test.log && echo "OK"
```

---

## 📊 EXEMPLO DE LOG

```
🚀 Iniciando scraping automático...

📍 Scraper SP (São Paulo)...
🌐 Abrindo página para SP...
⏳ Aguardando formulário...
📍 Selecionando SP...
⏳ Aguardando cidades...
🔍 Clicando em buscar...
⏳ Aguardando resultados...
✅ SP: 23 criados, 5 atualizados

📍 Scraper RJ (Rio de Janeiro)...
✅ RJ: 18 criados, 2 atualizados

[... mais estados ...]

✅ Scraping concluído em 2 minutos!
```

---

## ✅ CHECKLIST DE SETUP

- [ ] 1. Arquivo `scrape_caixa_real.py` criado ✅
- [ ] 2. Arquivo `scrapers_professional.py` criado ✅
- [ ] 3. Testar manualmente: `python manage.py scrape_caixa_real --estado SP`
- [ ] 4. Adicionar crontab (copie a linha acima)
- [ ] 5. Verificar com: `crontab -l`
- [ ] 6. Acompanhar logs: `tail -f /tmp/scraper.log`
- [ ] 7. Deixar rodando 24/7 🚀

---

## 🎯 PRÓXIMAS MELHORIAS

1. **Notificações quando falhar:**
```python
# Adicionar email/Slack se scraper falhar
```

2. **Banco de dados de histórico:**
```python
# Guardar quando rodou, quantos imóveis, sucesso/erro
```

3. **Dashboard de monitoramento:**
```python
# Ver último scraping, próximo agendado, sucesso rate
```

4. **Escalação para Celery:**
```python
# Quando ficar grande, mudar de Cron para Celery
```

---

## 📚 LEITURA COMPLEMENTAR

- Documentação do Cron: `man crontab`
- Cron Expression Generator: https://crontab.guru
- APScheduler Docs: https://apscheduler.readthedocs.io
- Celery Docs: https://docs.celeryproject.io

---

**Desenvolvido com ❤️ por Claude AI**
**LoteAlvo - Automação Profissional**
