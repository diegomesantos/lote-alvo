# Operacao e Sincronizacao dos Imoveis Caixa

Este documento descreve o fluxo atual de atualizacao dos imoveis da Caixa no LoteAlvo, cobrindo execucao local, producao, Celery, enriquecimento de detalhes, inativacao de imoveis vendidos/removidos, analise juridica IA e checklist de deploy.

## Resumo do fluxo

O sistema usa o CSV oficial da Caixa como fonte principal de dados.

Fluxo principal:

1. Baixa o CSV oficial em `media/caixa_csv`.
2. Le o CSV e identifica cada imovel por `imovel_id_caixa`.
3. Cria novos imoveis quando o ID ainda nao existe.
4. Atualiza imoveis existentes quando o ID ja existe.
5. Reativa imoveis que estavam inativos e voltaram no CSV.
6. Opcionalmente marca como inativos os imoveis ativos que nao vieram no CSV mais recente.
7. Em processo separado, enriquece imoveis ativos buscando pagina individual da Caixa para foto, edital, matricula e detalhes adicionais.

Arquivos principais:

- `apps/leiloes/caixa_csv.py`: download, leitura, importacao, inativacao e enriquecimento.
- `apps/leiloes/management/commands/sincronizar_caixa_csv.py`: comando operacional.
- `apps/leiloes/tasks.py`: tasks Celery para producao.
- `apps/leiloes/models.py`: campos de controle do imovel.
- `apps/leiloes/views.py`: listagem publica, filtrando apenas imoveis ativos.

## Campos de controle

O modelo `ImovelCaixa` tem campos especificos para controlar a disponibilidade na Caixa:

- `ativo_caixa`: indica se o imovel ainda aparece na lista oficial da Caixa.
- `ultima_sincronizacao_caixa`: data/hora da ultima vez em que o imovel apareceu no CSV importado.
- `removido_da_caixa_em`: data/hora em que o imovel deixou de aparecer no CSV e foi marcado como inativo.
- `detalhe_atualizado_em`: data/hora em que a pagina individual da Caixa foi enriquecida.

A pagina `/leiloes/` deve listar apenas `ativo_caixa=True`.

Imoveis removidos da Caixa nao sao apagados fisicamente. Eles ficam inativos para preservar auditoria, dados enriquecidos, favoritos e futuras analises.

## Importacao local

### Importar um CSV ja baixado

Use quando ja existir um arquivo em `media/caixa_csv`.

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --arquivo media/caixa_csv/Lista_imoveis_BA.csv
```

### Testar com poucas linhas

Use `--limite` para teste. Nunca use `--limite` junto com `--inativar-ausentes`, porque isso marcaria como inativos todos os imoveis fora do recorte.

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --arquivo media/caixa_csv/Lista_imoveis_BA.csv --limite 10
```

### Baixar o CSV geral da Caixa e importar

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado geral
```

### Baixar por UF

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado BA
```

Ou todos os estados, um CSV por UF:

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --todos-estados
```

### Sincronizacao completa com inativacao

Este e o modo correto para operacao real. Ele importa a lista oficial e marca como inativos os imoveis que nao vieram no CSV.

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado geral --inativar-ausentes
```

Para uma UF especifica:

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado BA --inativar-ausentes
```

Quando `--estado BA --inativar-ausentes` e usado, apenas imoveis de BA podem ser inativados.

## Enriquecimento local

O enriquecimento acessa a pagina individual da Caixa e tenta preencher:

- `foto_url`;
- `edital_url`;
- `matricula_url`;
- `descricao`;
- areas;
- quartos;
- datas;
- regras de pagamento;
- texto extraido da pagina;
- status de ocupacao quando identificado;
- sinais simples como presenca de palavra `penhora`.

Executar junto com a importacao:

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado BA --enriquecer --max-detalhes 100 --somente-pendentes-detalhe
```

Recomendacao: usar enriquecimento em lotes pequenos. Nao enriquecer dezenas de milhares de imoveis em uma unica execucao.

Paramentros relevantes:

- `--max-detalhes 100`: limita quantidade de paginas individuais acessadas.
- `--somente-pendentes-detalhe`: enriquece apenas imoveis sem `detalhe_atualizado_em`.
- `--intervalo 1.0`: pausa entre acessos para reduzir risco de bloqueio.
- `--headful`: abre navegador visivel para depuracao local.

## Producao com Celery

As tasks de producao ficam em `apps/leiloes/tasks.py`.

Tasks principais:

- `sincronizar_leiloes_caixa_csv_task`: baixa/importa o CSV geral e inativa ausentes.
- `sincronizar_estado_caixa_task(estado)`: baixa/importa uma UF e inativa ausentes daquela UF.
- `enriquecer_leiloes_caixa_pendentes_task`: enriquece imoveis ativos sem detalhe em lotes.
- `sincronizar_leiloes_caixa_task`: task antiga mantida por compatibilidade, agora apontando para o fluxo novo via CSV.

Agenda atual em `config/celery.py`:

- CSV geral a cada 6 horas.
- Enriquecimento de pendentes a cada hora, com lote de 300 e intervalo de 1 segundo.

Processos definidos no `Procfile`:

```Procfile
web: gunicorn config.wsgi --log-file -
worker: DJANGO_SETTINGS_MODULE=config.settings.production celery -A config worker -l info --concurrency=1
beat: DJANGO_SETTINGS_MODULE=config.settings.production celery -A config beat -l info
```

Em Railway ou plataforma equivalente, o ideal e ter servicos separados:

- Web: roda Django/Gunicorn.
- Worker: roda Celery worker.
- Beat: roda Celery beat.

### Railway

Arquivos preparados:

- `railway.toml`: servico Web. Roda migrations no `preDeployCommand` e inicia `gunicorn config.wsgi --log-file -`.
- `railway.worker.toml`: servico Worker. Inicia `celery -A config worker -l info --concurrency=1`.
- `railway.beat.toml`: servico Beat. Inicia `celery -A config beat -l info`.
- `nixpacks.toml`: build compartilhado, instalando Chromium/Playwright e Tesseract OCR.

No Railway, crie tres servicos apontando para o mesmo repositorio:

```text
Web    -> config-as-code /railway.toml
Worker -> config-as-code /railway.worker.toml
Beat   -> config-as-code /railway.beat.toml
```

Importante: a configuracao em arquivo sobrescreve a configuracao da dashboard para o deploy daquele servico. Portanto, o Worker e o Beat precisam apontar para seus respectivos arquivos de config; se usarem o `railway.toml` raiz, vao subir o processo web.

Referencias Railway:

- https://docs.railway.com/config-as-code
- https://docs.railway.com/builds/build-configuration
- https://docs.railway.com/deployments/start-command

Concorrencia do Worker:

- `--concurrency=1` foi escolhido porque o enriquecimento usa Playwright/Chromium e OCR, que consomem CPU/memoria.
- Se o plano de producao tiver mais CPU/RAM, pode subir para 2 ou criar outro Worker.
- Evitar muitos Workers simultaneos para nao aumentar bloqueios contra o site da Caixa.

## Variaveis de ambiente

Variaveis principais:

- `DATABASE_URL`: banco de producao.
- `SECRET_KEY`: chave do Django.
- `ALLOWED_HOSTS`: hosts permitidos.
- `DJANGO_SETTINGS_MODULE=config.settings.production`: recomendavel em todos os servicos de producao.
- `REDIS_URL`: Redis usado por Celery.
- `CELERY_BROKER_URL`: opcional; se ausente usa `REDIS_URL`.
- `CELERY_RESULT_BACKEND`: opcional; se ausente usa o broker.
- `OPENAI_API_KEY`: chave usada somente quando o usuario gerar a analise juridica IA.

O projeto tambem define:

- `CELERY_TASK_TIME_LIMIT`: padrao de 3 horas.
- `CELERY_TASK_SOFT_TIME_LIMIT`: padrao de 2 horas.
- `CELERY_WORKER_PREFETCH_MULTIPLIER=1`.
- `OPENAI_LEGAL_ANALYSIS_MODEL`: padrao `gpt-5.5`.
- `OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT`: padrao `medium`.
- `OPENAI_LEGAL_ANALYSIS_TEXT_LIMIT`: padrao `50000` caracteres de texto extraido.
- `OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS`: padrao `4500`.
- `OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB`: padrao `20`.
- `OPENAI_LEGAL_ANALYSIS_OCR_ENABLED`: padrao `True`.
- `OPENAI_LEGAL_ANALYSIS_OCR_LANG`: padrao `por+eng`.
- `OPENAI_LEGAL_ANALYSIS_OCR_DPI`: padrao `180`.
- `OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES`: padrao `25` paginas por documento.
- `OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS`: padrao `80`.
- `OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS`: padrao `45` por pagina.

## Playwright em producao

O download do CSV e o enriquecimento usam Playwright/Chromium.

No Railway/Nixpacks, a instalacao do Chromium e do Tesseract OCR esta automatizada em:

```text
nixpacks.toml
```

O setup instala os pacotes APT:

```text
tesseract-ocr
tesseract-ocr-por
```

O build tambem executa:

```bash
PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright python -m playwright install --with-deps chromium
```

Esse comando baixa o Chromium e instala as dependencias de sistema necessarias no container. A variavel `PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright` faz o runtime procurar o navegador no mesmo caminho gravado durante o build.

Se o worker falhar com erro de navegador ausente, verificar:

- se o deploy usou o `nixpacks.toml`;
- se o log de build executou `python -m playwright install --with-deps chromium`;
- se o provedor manteve `PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright` na imagem/runtime.

Se a analise juridica falhar por OCR ausente, verificar no log de build a instalacao de `tesseract-ocr` e `tesseract-ocr-por`.

## CSVs, fotos e PDFs

### CSVs

CSVs baixados ficam em:

```text
media/caixa_csv/
```

Eles sao artefatos operacionais. Podem ser limpos periodicamente se ocuparem muito espaco.

### Fotos

Fotos sao servidas pelo endpoint local `leiloes:imagem`, com cache em:

```text
media/caixa_fotos/
```

O cache local evita depender de hotlink direto para as imagens da Caixa nos cards.

### PDFs

Atualmente os PDFs nao sao armazenados. O sistema salva apenas os links:

- `edital_url`;
- `matricula_url`.

A analise juridica IA le esses documentos sob demanda quando o usuario clica em gerar/atualizar analise. O fluxo e:

1. baixa o edital/matricula pelo link oficial da Caixa;
2. extrai texto em memoria com `pypdf`;
3. se uma pagina tiver pouco texto nativo, renderiza a pagina com PyMuPDF e roda OCR local com Tesseract;
4. envia o texto extraido para a OpenAI;
5. salva no campo JSON `ImovelCaixa.detalhes["analise_juridica_ia"]` somente o resultado, metadados das fontes e status operacional.

O texto integral do PDF nao fica salvo no banco. O PDF tambem nao fica salvo em `media/`.

Backblaze B2 nao e necessario para a IA ler os documentos nessa fase. Ele passa a fazer sentido se quisermos cache, auditoria, trilha de evidencia ou reprocessamento sem depender da Caixa.

Modelo recomendado para uma proxima fase:

```text
caixa-documentos/
  {imovel_id_caixa}/
    edital.pdf
    matricula.pdf
```

O banco guardaria URL/metadata do arquivo, hash, tamanho e data de download. Por enquanto isso nao foi implementado.

## Analise juridica IA

A rota de detalhes do imovel exibe a secao "Analise juridica IA".

Rota de acao:

```text
POST /leiloes/analise-juridica/<imovel_id_caixa>/
```

Caracteristicas:

- exige usuario autenticado;
- nao roda automaticamente na sincronizacao;
- nao roda ao abrir a pagina;
- gera a analise apenas por clique do usuario;
- cacheia o ultimo resultado no JSON `detalhes`;
- permite atualizar a analise pelo mesmo botao;
- se `OPENAI_API_KEY` nao estiver configurada, salva status `sem_api_key` e mostra mensagem controlada;
- se matricula/edital nao existirem, salva status `sem_documentos`;
- se o PDF for escaneado, tenta OCR local antes de declarar `sem_texto`;
- se mesmo com OCR nao houver texto util, salva status `sem_texto`.

Arquivos principais:

```text
apps/leiloes/analise_juridica.py
apps/leiloes/views.py
templates/leiloes/detalhe.html
```

O prompt pede triagem juridica informativa, nao parecer final. A resposta e estruturada para cobrir:

- resumo executivo;
- nivel e score de risco;
- alertas principais com evidencia e fonte;
- ocupacao;
- onus, gravames e restricoes;
- debitos e responsabilidades;
- processos mencionados nos documentos;
- cadeia de titularidade;
- pontos a validar;
- limites da analise.

OCR:

- usa `pypdf` primeiro;
- usa PyMuPDF apenas para renderizar paginas que tenham pouco texto nativo;
- usa Tesseract com idioma `por+eng`;
- limita o OCR por documento com `OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES`;
- registra em `fontes` quantas paginas foram processadas com OCR e eventuais erros.

Importante: quando `OPENAI_API_KEY` estiver ativa, o texto extraido da matricula/edital sera enviado para a OpenAI para processamento. Se a politica do produto exigir retencao local, trilha probatoria ou revisao humana, implementar Backblaze B2 e tabela de documentos antes de habilitar em producao.

## Regra de atualizacao e substituicao

O campo `imovel_id_caixa` e a chave unica.

Quando o CSV traz um ID ja existente:

- campos principais do CSV sao atualizados;
- o imovel e marcado como `ativo_caixa=True`;
- `ultima_sincronizacao_caixa` e atualizada;
- `removido_da_caixa_em` volta para `None`;
- detalhes ja enriquecidos sao preservados;
- formas de pagamento existentes sao mescladas com as formas vindas do CSV.

Quando o CSV traz um ID novo:

- um novo `ImovelCaixa` e criado.

Quando uma sincronizacao completa termina:

- imoveis ativos que nao apareceram no CSV sao marcados como `ativo_caixa=False`;
- `removido_da_caixa_em` e preenchido;
- esses imoveis deixam de aparecer em `/leiloes/`.

## Cuidados operacionais

Nao usar:

```bash
--limite ... --inativar-ausentes
```

O comando bloqueia essa combinacao para evitar inativacao incorreta.

Evitar:

- enriquecer todos os imoveis em uma unica execucao;
- rodar muitos workers de enriquecimento em paralelo contra a Caixa;
- depender de filesystem local para documentos importantes em producao;
- apagar fisicamente imoveis vendidos/removidos.

Preferir:

- CSV geral para sincronizacao principal;
- enriquecimento separado em lotes;
- soft delete via `ativo_caixa=False`;
- Backblaze B2 apenas quando decidirmos armazenar PDFs.

## Validacoes uteis

Checar integridade Django:

```bash
.venv/bin/python manage.py check
```

Checar migrations pendentes:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
```

Contar ativos e inativos:

```bash
.venv/bin/python manage.py shell -c "from apps.leiloes.models import ImovelCaixa; print(ImovelCaixa.objects.filter(ativo_caixa=True).count(), ImovelCaixa.objects.filter(ativo_caixa=False).count())"
```

Contar documentos enriquecidos:

```bash
.venv/bin/python manage.py shell -c "from apps.leiloes.models import ImovelCaixa; print('edital', ImovelCaixa.objects.exclude(edital_url__isnull=True).exclude(edital_url='').count()); print('matricula', ImovelCaixa.objects.exclude(matricula_url__isnull=True).exclude(matricula_url='').count()); print('detalhes', ImovelCaixa.objects.exclude(detalhe_atualizado_em__isnull=True).count())"
```

Testar renderizacao da listagem:

```bash
.venv/bin/python manage.py shell -c "from django.test import Client; r=Client().get('/leiloes/'); print(r.status_code, b'Explorador de Leil' in r.content)"
```

## Solucao de problemas

### CSV nao baixa

Possiveis causas:

- Caixa exibiu CAPTCHA/bloqueio.
- Chromium/Playwright nao foi instalado no build.
- Instabilidade temporaria no site da Caixa.

Acao:

- testar local com `--headful`;
- confirmar no log de build a execucao de `python -m playwright install --with-deps chromium`;
- reduzir frequencia de execucao se houver bloqueios.

### Enriquecimento com muitos erros

Possiveis causas:

- bloqueio temporario da Caixa;
- layout da pagina mudou;
- link individual invalido/removido.

Acao:

- reduzir `max_detalhes`;
- aumentar `--intervalo`;
- testar um imovel manualmente;
- revisar `extrair_detalhes_html` em `apps/leiloes/caixa_csv.py`.

### Imoveis sumiram da listagem

Verificar se foram marcados como inativos:

```bash
.venv/bin/python manage.py shell -c "from apps.leiloes.models import ImovelCaixa; print(ImovelCaixa.objects.filter(ativo_caixa=False).order_by('-removido_da_caixa_em').values_list('imovel_id_caixa', 'estado', 'removido_da_caixa_em')[:10])"
```

Se a inativacao foi causada por uma sincronizacao incompleta, rodar novamente uma sincronizacao completa sem `--limite`:

```bash
.venv/bin/python manage.py sincronizar_caixa_csv --estado geral --inativar-ausentes
```

## Pagina de detalhes do imovel

A pagina de detalhes foi implementada com uma rota clicavel a partir dos cards:

```text
/leiloes/<imovel_id_caixa>/
```

Escopo implementado no MVP:

- card clicavel na listagem;
- foto principal usando o endpoint/cache local de imagens;
- painel lateral com valor, desconto, modalidade, data e botao para Caixa;
- endereco completo;
- caracteristicas do imovel;
- condicoes de oferta;
- formas de pagamento;
- situacao de ocupacao quando disponivel;
- documentos com links para edital/matricula;
- analise juridica IA sob demanda com resultado cacheado no imovel;
- bloco de dados extraidos da pagina da Caixa;
- acao de simulacao;
- acao para cadastrar o imovel em Meus Imoveis, criando o card na etapa `estoque`;
- mensagem clara quando dados enriquecidos ainda nao estiverem disponiveis.

Ao cadastrar em Meus Imoveis, o sistema preenche automaticamente:

- endereco, cidade, UF e tipo do imovel;
- etapa `estoque`;
- prioridade `media`;
- tipo de leilao;
- data do leilao/oferta quando existir;
- link oficial da Caixa;
- avaliacao e lance;
- preco de venda inicial igual ao valor de avaliacao;
- observacoes com ID Caixa, modalidade, bairro, aceite de financiamento/FGTS/consorcio e links de edital/matricula quando existirem.

O campo `caixa_imovel_id` em `apps.imoveis.Imovel` evita duplicidade por usuario. Se o usuario tentar cadastrar o mesmo imovel novamente, o sistema reaproveita o card existente.

Fora do MVP:

- historico de precos;
- armazenamento de PDFs no Backblaze;
- consulta processual por CPF.

## Checklist de producao

Antes do deploy:

- rotacionar qualquer chave OpenAI que tenha sido compartilhada fora do cofre de segredos;
- criar PostgreSQL e Redis no Railway;
- configurar `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE=config.settings.production` e `OPENAI_API_KEY` nos tres servicos;
- confirmar que Worker e Beat usam os arquivos `railway.worker.toml` e `railway.beat.toml`;
- confirmar que o build executa `python -m playwright install --with-deps chromium`;
- confirmar no log de build a instalacao de `tesseract-ocr` e `tesseract-ocr-por`;
- aplicar dominio/host final em `ALLOWED_HOSTS`.

Depois do deploy:

- verificar `/accounts/login/`;
- criar uma conta e confirmar login por e-mail;
- acompanhar logs do Worker e do Beat por pelo menos um ciclo;
- rodar uma sincronizacao manual inicial, se necessario:

```bash
python manage.py sincronizar_caixa_csv --estado geral --inativar-ausentes --settings=config.settings.production
```

- abrir `/leiloes/` e confirmar filtros, paginacao e cards;
- abrir um detalhe de imovel enriquecido e confirmar foto, documentos, botao Caixa e cadastro em Meus Imoveis;
- gerar uma analise juridica IA em um imovel com matricula digitalizada e confirmar se a fonte mostra paginas processadas por OCR.

Fase posterior:

- melhorar OCR com pre-processamento de imagem, se os documentos reais tiverem baixa qualidade;
- consultar processos por CPF/CNPJ somente com fonte/API confiavel e regra clara de privacidade;
- opcionalmente armazenar PDFs no Backblaze para cache/auditoria.
