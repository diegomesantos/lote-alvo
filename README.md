# Smart Leilão 🏠🔨

Sistema web de exploração e análise de leilões de imóveis da Caixa Econômica Federal com suporte a filtros avançados, simulador financeiro e gestão de propriedades.

## 🌟 Funcionalidades

### Explorador de Leilões
- **Filtros Avançados**: Estado, Cidade, Bairro, Tipo de imóvel
- **Busca Textual**: Por endereço, cidade ou bairro
- **Filtros de Valor**: Range mínimo e máximo de lances
- **Desconto**: Faixas de 0-10%, 10-20%, 20-30%, 30%+
- **Formas de Pagamento**: Financiamento, FGTS, Consórcio
- **Ordenação**: Mais recentes, menor/maior valor, maior desconto, modalidade
- **Paginação Configurável**: 12, 24, 36 ou 48 itens por página

### Cards de Imóvel
- Foto do imóvel com fallback
- Localização completa (endereço, cidade, estado, bairro)
- Características (tipo, modalidade, área, quartos)
- Valores (avaliação, desconto, lance mínimo, valor/m²)
- Status de ocupação e pendências
- Links para edital, matrícula e site da Caixa
- Botão de simulação rápida

### Simulador Financeiro
- Cálculo de lance final com base em avaliação e desconto
- Análise de custos (cartório, registro, etc.)
- Projeção de retorno
- Giro de capital

### Gestão de Imóveis
- Adicionar imóveis favoritos à plataforma
- Kanban de controle de etapas (estoque, pré-seleção, análise, negociação, arrematado)
- Dashboard financeiro
- Histórico de lances

### Análise Jurídica (IA)
- Análise automática de documentos (edital, matrícula)
- Detecção de riscos (penhora, ocupação, pendências)
- Classificação de risco (baixo, médio, alto, crítico)

## 🛠️ Stack Técnico

### Backend
- **Framework**: Django 4.x
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Web Server**: Gunicorn
- **Python**: 3.10+

### Frontend
- **Styling**: Tailwind CSS
- **JavaScript**: Alpine.js, HTMX
- **Templates**: Django Templates

### Integração Externa
- Caixa Econômica Federal (web scraping)
- Claude AI (análise jurídica)

## 📦 Instalação Local

### Pré-requisitos
- Python 3.10+
- PostgreSQL 12+
- Redis 6+

### Setup

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/smart-leilao.git
cd smart-leilao
```

2. **Crie ambiente virtual**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

3. **Instale dependências**
```bash
pip install -r requirements.txt
```

4. **Configure variáveis de ambiente**
```bash
cp .env.example .env
# Edite .env com suas credenciais
```

5. **Rode migrações**
```bash
python manage.py migrate
```

6. **Crie superuser**
```bash
python manage.py createsuperuser
```

7. **Carregue dados de teste**
```bash
python manage.py populate_test_data
```

8. **Inicie servidor**
```bash
python manage.py runserver
```

Acesse em `http://localhost:8000`

## 🚀 Deploy no Railway

### Pré-requisitos
- Conta no [Railway.app](https://railway.app)
- GitHub conectado

### Configuração Automática via Railway CLI

```bash
# Instale Railway CLI
npm i -g @railway/cli

# Faça login
railway login

# Crie novo projeto
railway init

# Deploy
railway up
```

### Configuração Manual via Dashboard

1. **Nova aplicação** no Dashboard Railway
2. **Conecte o GitHub**
3. **Selecione este repositório**
4. **Variables** → Configure:
   - `RAILWAY_ENVIRONMENT=production`
   - `DJANGO_SECRET_KEY=` (gere uma nova)
   - `ALLOWED_HOSTS=seu-dominio.railway.app`
   - `DEBUG=False`
   - `APIFY_API_TOKEN=` (se usar scrapers)
   - `CLAUDE_API_KEY=` (para análise jurídica)

5. **Add Service** → PostgreSQL
6. **Add Service** → Redis
7. Deixe Railway executar migrações automaticamente

### Arquivos de Configuração

- **`railway.toml`** - Web service (Gunicorn)
- **`railway.worker.toml`** - Celery worker
- **`railway.beat.toml`** - Celery beat (scheduler)
- **`nixpacks.toml`** - Build configuration

## 📚 Documentação

### Estrutura de Pasta
```
smart_leilao/
├── apps/
│   ├── leiloes/         # Explorador e detalhes de leilões
│   ├── imoveis/         # Gestão de imóveis do usuário
│   ├── financeiro/      # Dashboard financeiro
│   ├── calculadora/     # Simulador
│   └── accounts/        # Autenticação
├── config/              # Configurações Django
├── core/                # Utilitários (cálculos, tags)
├── templates/           # Templates HTML
├── static/              # Assets estáticos
└── manage.py
```

### Models Principais

**ImovelCaixa**
- Imóveis da Caixa com dados brutos
- Campos: endereço, valor, desconto, localização
- Sincronizado via web scraping

**Imovel**
- Imóveis do usuário (favoritos)
- Relacionado ao ImovelCaixa
- Rastreia etapa, prioridade, notas

**Lancamento**
- Histórico financeiro de cada imóvel
- Entrada/saída, categoria, data

## 🔧 Configuração Avançada

### Scraper da Caixa
```bash
python manage.py sincronizar_caixa SP --modo-teste
```

### Análise Jurídica
Requer `CLAUDE_API_KEY` na variável de ambiente.

### Celery Tasks
```bash
# Worker
celery -A config worker -l info

# Beat (scheduler)
celery -A config beat -l info
```

## 🔒 Segurança

- `DEBUG=False` em produção
- Senhas armazenadas com hash Django
- CSRF protection habilitada
- HTTPS obrigatório (Railway configura automaticamente)
- Variáveis sensíveis em environment variables

## 📝 Licença

Proprietário - 2024

## 👨‍💻 Autor

Diego Gomes Santos

## 🐛 Issues & Contribuições

Para reportar bugs ou sugerir funcionalidades, abra uma issue no GitHub.

---

**Status**: Em desenvolvimento ✨
