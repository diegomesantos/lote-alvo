# 🔐 Variáveis de Ambiente - Railway Setup

## ⚡ TL;DR - Comece com Essas 5 Variáveis

```
SECRET_KEY=u@u7+@2^6k+yr9s6idivsxa74g=#ph+ameu(j*y=_825^f$$rz
DEBUG=False
ALLOWED_HOSTS=*.railway.app
DJANGO_SETTINGS_MODULE=config.settings.production
CSRF_TRUSTED_ORIGINS=https://*.railway.app
```

**Banco e Cache**: Railway cria automaticamente quando você adiciona PostgreSQL e Redis

---

## 📖 Guia Completo

### 1️⃣ OBRIGATÓRIAS (5 variáveis)

#### SECRET_KEY
- **O quê**: Chave de segurança do Django
- **Valor**: `u@u7+@2^6k+yr9s6idivsxa74g=#ph+ameu(j*y=_825^f$$rz` (use a gerada acima)
- **⚠️ IMPORTANTE**: Use uma chave NOVA, nunca reutilize de desenvolvimento

#### DEBUG
- **O quê**: Ativa modo debug
- **Valor**: `False` (SEMPRE False em produção!)
- **Risco**: Se True, expõe informações sensíveis

#### ALLOWED_HOSTS
- **O quê**: Domínios que podem acessar a app
- **Valor inicial**: `*.railway.app`
- **Depois**: Quando configurar domínio próprio: `seu-dominio.com.br,*.railway.app`

#### DJANGO_SETTINGS_MODULE
- **O quê**: Qual arquivo de settings usar
- **Valor**: `config.settings.production`
- **Não mude**: Já está configurado para produção

#### CSRF_TRUSTED_ORIGINS
- **O quê**: Origens confiáveis para CSRF protection
- **Valor**: `https://*.railway.app`
- **Depois**: Quando tiver domínio próprio: `https://seu-dominio.com.br,https://*.railway.app`
- **Formato**: URLs completas com https://

---

### 2️⃣ AUTO-CRIADAS PELO RAILWAY

Quando você adicionar serviços no Railway, ele preenche automaticamente:

#### DATABASE_URL
- **O quê**: Conexão com PostgreSQL
- **Criada**: Ao adicionar "Add Service → PostgreSQL"
- **Não mude**: Railway gerencia automaticamente

#### REDIS_URL
- **O quê**: Conexão com Redis (Cache e Celery)
- **Criada**: Ao adicionar "Add Service → Redis"
- **Não mude**: Railway gerencia automaticamente

---

### 3️⃣ OPCIONAIS (Funcionalidades extras)

#### OPENAI_API_KEY
- **Para quê**: Análise jurídica automática de documentos
- **Status**: Opcional - deixe vazio por enquanto
- **Como obter**: https://platform.openai.com/api-keys
- **Usar depois**: Quando quiser análise de edital/matrícula

#### OPENAI_LEGAL_ANALYSIS_MODEL
- **Padrão**: `gpt-5.5`
- **Alternativas**: `gpt-4o` (melhor custo), `gpt-4-turbo`, `gpt-4`
- **Recomendado**: `gpt-4o`

Outros parâmetros OpenAI:
- `OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT=medium`
- `OPENAI_LEGAL_ANALYSIS_TEXT_LIMIT=50000`
- `OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS=4500`
- `OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB=20`
- `OPENAI_LEGAL_ANALYSIS_OCR_ENABLED=True`
- `OPENAI_LEGAL_ANALYSIS_OCR_LANG=por+eng`
- `OPENAI_LEGAL_ANALYSIS_OCR_DPI=180`
- `OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES=25`
- `OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS=80`
- `OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS=45`

---

## 🚀 Passo-a-Passo no Railway

### Passo 1: Acessar Railway
1. Vá para https://railway.app
2. Login com GitHub
3. Click "Create New Project"
4. Select "Deploy from GitHub repo"

### Passo 2: Conectar Repositório
1. Selecione `lote-alvo`
2. Railway detecta Django automaticamente
3. Aguarde o build (vai dizer qual Docker image usar)

### Passo 3: Adicionar PostgreSQL
1. Click "Add Service"
2. Select "PostgreSQL"
3. Railway cria DATABASE_URL automaticamente

### Passo 4: Adicionar Redis
1. Click "Add Service"
2. Select "Redis"
3. Railway cria REDIS_URL automaticamente

### Passo 5: Configurar Variáveis
1. Vá para "Variables"
2. Clique "Add Variable" e preencha:

```
SECRET_KEY = u@u7+@2^6k+yr9s6idivsxa74g=#ph+ameu(j*y=_825^f$$rz
DEBUG = False
ALLOWED_HOSTS = *.railway.app
DJANGO_SETTINGS_MODULE = config.settings.production
```

### Passo 6: Deploy
1. Clique "Deploy"
2. Railway faz build e deploy automático
3. Aguarde 2-5 minutos
4. Acesse a URL gerada (ex: `https://lote-alvo-prod-xxxx.railway.app`)

---

## ✅ Checklist Rápido

- [ ] SECRET_KEY adicionada
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS = *.railway.app
- [ ] DJANGO_SETTINGS_MODULE = config.settings.production
- [ ] CSRF_TRUSTED_ORIGINS = https://*.railway.app
- [ ] PostgreSQL adicionado (DATABASE_URL auto)
- [ ] Redis adicionado (REDIS_URL auto)
- [ ] Deploy iniciado

---

## 🐛 Troubleshooting

**Erro 500 no deploy?**
```bash
railway logs
```
Veja a mensagem de erro e procure por variável faltante.

**Banco de dados não conecta?**
- Verifique se PostgreSQL está "Running" na aba Plugins
- DATABASE_URL deve estar preenchida automaticamente

**Erro de SECRET_KEY?**
- Gere uma nova:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**Aplicação lenta?**
- Aumente recursos (CPU/RAM) na aba "Settings"
- Padrão é suficiente para começar

---

## 📞 Suporte

- **Railway Docs**: https://docs.railway.app
- **Django Docs**: https://docs.djangoproject.com
- **GitHub Issues**: https://github.com/diegomesantos/lote-alvo/issues

---

**Tudo pronto! Seu deploy está a apenas alguns cliques de distância.** 🚀
