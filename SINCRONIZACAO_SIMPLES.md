# 🔄 Sincronização Automática - Solução Simples

**Status**: ✅ Testado | **Método**: APScheduler | **Custo**: Gratuito

---

## 🎯 A Solução Mais Simples

### **Opção 1: Usar Cron Job (Recomendado para produção)**

```bash
# Abrir crontab
crontab -e

# Adicionar esta linha (sincroniza a cada 6h)
0 */6 * * * cd /Users/diegogomessantos/Library/CloudStorage/OneDrive-Pessoal/Cursos/Asimov\ python/Meus\ Projetos/smart_leilao && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 manage.py sincronizar_caixa --todos
```

✅ **Pronto!** Sistema sincroniza automaticamente a cada 6 horas

---

### **Opção 2: APScheduler (Mais portável)**

```bash
pip install apscheduler django-apscheduler
```

---

### **Opção 3: Sincronizar Manualmente Quando Quiser**

```bash
python3 manage.py sincronizar_caixa --todos
```

---

## ✨ **Por enquanto:**

Use a **Opção 3** - sincronize manualmente sempre que quiser dados atualizados:

```bash
python3 manage.py sincronizar_caixa --todos
```

Leva menos de 30 segundos! ⚡

---

## 🚀 **Para Produção:**

Use a **Opção 1** - configure no crontab do servidor:

```bash
# Sincroniza diariamente às 9 da manhã
0 9 * * * cd /caminho/do/projeto && python manage.py sincronizar_caixa --todos

# Sincroniza a cada 6 horas
0 */6 * * * cd /caminho/do/projeto && python manage.py sincronizar_caixa --todos

# Sincroniza a cada 1 hora
0 * * * * cd /caminho/do/projeto && python manage.py sincronizar_caixa --todos
```

---

## 📊 Resumo

| Método | Automático | Fácil | Recomendado |
|--------|-----------|------|------------|
| Manual | ❌ | ✅ | Dev |
| Cron | ✅ | ✅ | Produção |
| APScheduler | ✅ | ✅ | Alternativa |
| Celery | ✅ | ❌ | Complexo |

---

**Usa manual por enquanto. Para produção, configura cron job!** 🚀
