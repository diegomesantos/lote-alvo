# 🚀 Guia: GitHub + Railway Setup

## Passo 1: Criar Repositório no GitHub

### Via Website (Recomendado)

1. Acesse [github.com/new](https://github.com/new)
2. **Repository name**: `smart-leilao`
3. **Description**: Smart Leilão - Platform for exploring and analyzing CEF real estate auctions
4. **Public** ou **Private** (escolha sua preferência)
5. **NÃO** inicie com README/gitignore/license (já temos)
6. Clique **Create repository**

### Via GitHub CLI

```bash
gh repo create smart-leilao \
  --public \
  --source=. \
  --remote=origin \
  --push
```

---

## Passo 2: Conectar seu Git Local ao GitHub

Se criou via website, execute isto:

```bash
cd "/Users/diegogomessantos/Library/CloudStorage/OneDrive-Pessoal/Cursos/Asimov python/Meus Projetos/smart_leilao"

# Adicione o remote (substitua SEU_USUARIO)
git remote add origin https://github.com/SEU_USUARIO/smart-leilao.git

# Configure a branch padrão
git branch -M main

# Faça o push inicial
git push -u origin main
```

**Resultado esperado:**
```
Counting objects: 122, done.
Compressing objects: 100% (118/118), done.
Writing objects: 100% (122/122)...
remote: Create a pull request for 'main' on GitHub...
```

---

## Passo 3: Verificar Configuração SSH (Opcional mas Recomendado)

Para não digitar senha toda vez:

```bash
# Gere chave SSH se não tiver
ssh-keygen -t ed25519 -C "diego.gsantos@live.com"

# Adicione ao seu GitHub:
# GitHub Settings → SSH and GPG keys → New SSH key
# Cole o conteúdo de ~/.ssh/id_ed25519.pub

# Teste a conexão
ssh -T git@github.com
```

---

## Passo 4: Deploy no Railway

### Opção A: Via Railway Dashboard (Mais Fácil)

1. Acesse [railway.app](https://railway.app)
2. **Login** com GitHub
3. **New Project** → **Deploy from GitHub repo**
4. **Autorize** o Railway no GitHub
5. Selecione `smart-leilao`
6. Railway detecta automaticamente Django (Nixpacks)
7. Clique **Deploy**

#### Configure as Variáveis de Ambiente

No dashboard Railway, vá para **Variables**:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=*.railway.app,seu-dominio-custom.com
ENVIRONMENT=production

# Database (será criada automaticamente)
DATABASE_URL=postgresql://...  # Railway preenche automaticamente

# Redis (será criada automaticamente)
REDIS_URL=redis://...  # Railway preenche automaticamente

# APIs Externas (opcional)
APIFY_API_TOKEN=your-apify-token
CLAUDE_API_KEY=your-claude-api-key

# Email (opcional, para envio de notificações)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Opção B: Via Railway CLI

```bash
# Instale Railway CLI
npm i -g @railway/cli

# Faça login
railway login

# No diretório do projeto
railway init
railway up
```

---

## Passo 5: Adicionar Serviços no Railway

O Railway **detecta automaticamente** via `requirements.txt`:
- ✅ PostgreSQL
- ✅ Redis

Se precisar adicionar manualmente:

1. **New Service** → **Database** → **PostgreSQL**
2. **New Service** → **Redis**

---

## Passo 6: Migrações Automáticas

Railway executa automaticamente:
```bash
python manage.py migrate
```

Se precisar em produção:
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

---

## Passo 7: Deploy Contínuo

Railway configura automaticamente **CI/CD**:
- Toda vez que você faz `git push` para `main`
- Railway detecta mudanças
- Executa build
- Deploy automático se bem-sucedido

---

## Checklist Final

### GitHub
- [x] Repositório criado
- [x] Código com git init
- [x] 2 commits feitos
- [x] Remote configurado
- [x] Push para main

### Railway
- [ ] Criar novo projeto
- [ ] Conectar com GitHub
- [ ] Selecionar repositório
- [ ] Configurar variáveis de ambiente
- [ ] Adicionar domínio customizado (opcional)
- [ ] Configurar CD/CI
- [ ] Executar primeira migração
- [ ] Testar em produção

### Após Deploy
- [ ] Acessar URL do Railway
- [ ] Fazer login como admin
- [ ] Sincronizar dados de leilões
- [ ] Testar filtros
- [ ] Configurar domínio customizado

---

## URLs Úteis

| Serviço | URL |
|---------|-----|
| GitHub | https://github.com/SEU_USUARIO/smart-leilao |
| Railway Project | https://railway.app/project/PROJECT_ID |
| App em Produção | https://seu-app.railway.app |
| Django Admin | https://seu-app.railway.app/admin |
| Explorador | https://seu-app.railway.app/leiloes |

---

## Troubleshooting

### Erro: "fatal: No remote named 'origin'"
```bash
git remote add origin https://github.com/SEU_USUARIO/smart-leilao.git
git push -u origin main
```

### Erro 500 no Railway
```bash
# Verifique logs
railway logs

# Verifique variáveis de ambiente
railway run python manage.py check
```

### Migrações falhando
```bash
railway run python manage.py migrate --noinput
railway run python manage.py collectstatic --noinput
```

### Imagens não carregando
Certifique-se que `STATIC_URL = '/static/'` e `MEDIA_URL = '/media/'` estão configurados.

---

## Próximos Passos

1. ✅ Setup GitHub + Railway
2. 📧 Configurar SMTP para envio de emails
3. 🔐 Configurar domínio customizado no Railway
4. 📊 Configurar backups de banco de dados
5. 🔄 Configurar Celery workers para sincronização
6. 🎯 Configurar monitoramento e alertas

---

**Última atualização**: 2024-06-04
**Status**: Pronto para deployment 🚀
