# Operação de Custos Cartorários

Este fluxo controla as estimativas de escritura, registro e fundos extras usados na calculadora e nas páginas dos imóveis.

## Modelo adotado

- As tabelas oficiais ficam versionadas no banco em `Calculadora > Tabelas cartorárias`.
- Cada tabela possui UF, ano, tipo, vigência, fonte oficial, status e faixas de valor.
- Regras extras por UF, como fundos estaduais, ficam em `Calculadora > Regras extras cartorárias`.
- O cálculo sempre tenta usar a tabela vigente do banco. Se não existir tabela válida para a UF/tipo, cai para a tabela legada do código. Se a UF também não existir no legado, usa estimativa interna.

## Status

- `Pendente de validação`: tabela importada ou cadastrada, mas ainda não conferida manualmente na fonte oficial.
- `Validada`: tabela conferida contra a fonte oficial e liberada para uso com maior confiança.
- `Substituída`: tabela mantida apenas como histórico.

## Carga inicial

Depois de aplicar as migrations, rode:

```bash
python manage.py seed_cartorio_tabelas --replace
```

No Railway:

```bash
railway run --service lote-alvo python manage.py seed_cartorio_tabelas --replace
```

Por padrão o seed cria as tabelas como `pendente_validacao`. Depois da conferência, marque as tabelas no admin como `validada`.

Quando houver URL oficial cadastrada no seed, o comando também cria uma `Fonte cartorária monitorada`.

## Monitoramento automático das fontes

O sistema possui um monitoramento das fontes oficiais com aplicação automática:

- `Calculadora > Fontes cartorárias monitoradas`: URLs oficiais acompanhadas pelo sistema.
- `Calculadora > Eventos de fonte cartorária`: fila de revisão quando uma fonte muda ou falha.
- Celery beat executa `monitorar_fontes_cartorio_task` semanalmente, toda segunda-feira às 07:30.
- Quando uma fonte muda, o sistema **tenta extrair e aplicar a nova tabela automaticamente** (ver abaixo).
- Se a aplicação automática não for possível, o sistema marca as tabelas e regras extras vinculadas àquela fonte como `pendente_validacao` para revisão manual.

### Aplicação automática (parser)

`apps/calculadora/services/cartorio_parsers.py` contém o motor de extração:

- Cada UF pode registrar um parser em `PARSERS` que recebe o conteúdo baixado e devolve as faixas de escritura/registro. Hoje há parsers para **BA, MG, SC, GO, PE, RS e SP** (a fonte monitorada de cada uma aponta para o PDF/planilha oficial em `FONTE_TABELA_URL`). UFs sem parser (PR, RJ, CE, DF, ES) caem direto na revisão manual.
- O SP usa duas fontes: o PDF de Registro (monitorado) e a planilha de Notas (baixada pelo parser via `fetch`).
- As URLs das tabelas têm o ano no caminho; quando o TJ publicar a do ano seguinte numa URL nova, a fonte antiga retorna 404 (vira evento de erro) — basta atualizar a URL em `FONTE_TABELA_URL`.
- As faixas extraídas passam por **guardas de sanidade** (`validar_faixas`): quantidade mínima de faixas, valores estritamente crescentes e dentro de uma faixa plausível, limites crescentes e última faixa "sem limite".
- Se as faixas passam nas guardas, o sistema cria uma **nova `CartorioTabela` vigente a partir de hoje** (status `validada`), aposenta a anterior (`substituida` + `vigente_fim`) e marca o evento como `revisado` com `aplicacao_automatica = True`.
- Se o parse falha ou reprova nas guardas, **nada é gravado**: o sistema cai no fluxo de revisão manual (marca `pendente_validacao`). Isso evita publicar um valor "plausível-porém-errado" quando o PDF do TJ vier quebrado.
- A aplicação automática pode ser desligada com `CARTORIO_AUTO_APLICAR_TABELAS = False` no settings (padrão: ligada).

Para cobrir uma nova UF, registre um parser em `PARSERS` (UF → função) que devolva `{"escritura": [(limite, valor), ...], "registro": [...]}` a partir do conteúdo oficial.

Você não precisa rodar o comando abaixo na rotina de produção se o serviço Beat estiver ativo. Ele existe apenas para teste, implantação inicial ou execução avulsa:

```bash
python manage.py monitorar_fontes_cartorio
```

Filtrando uma UF:

```bash
python manage.py monitorar_fontes_cartorio --uf BA
```

No Railway, execute dentro do serviço web:

```bash
railway ssh --service lote-alvo /opt/venv/bin/python manage.py monitorar_fontes_cartorio --skip-checks
```

O monitoramento calcula hash do conteúdo oficial e cria um evento quando detecta mudança. Em seguida tenta a aplicação automática (parser + guardas). Quando aplica, o evento já nasce `revisado` com a tabela nova vigente. Quando não consegue aplicar, o evento fica `pendente` e as tabelas/regras vinculadas vão para `pendente_validacao`.

Fluxo recomendado quando surgir evento **pendente** (parser não aplicou):

1. Abrir o evento em `Calculadora > Eventos de fonte cartorária`.
2. Abrir a URL oficial da fonte.
3. Conferir se houve nova tabela, ato normativo ou alteração de faixa.
4. Atualizar as faixas se a fonte oficial tiver mudado os valores.
5. Conferir os valores manualmente.
6. Marcar a tabela como `validada`.
7. Marcar o evento de fonte como `revisado` ou `ignorado`.

## Rotina anual

1. Consultar a tabela oficial publicada pelo TJ do estado ou órgão extrajudicial competente.
2. Criar uma nova `Tabela cartorária` para a UF, tipo e ano, com `vigente_inicio`.
3. Cadastrar as faixas na ordem correta. A última faixa pode ficar com limite superior vazio para representar "sem limite".
4. Conferir escritura, registro e regras extras separadamente.
5. Marcar a tabela anterior como `substituida` ou preencher `vigente_fim`.
6. Marcar a nova tabela como `validada` somente depois da conferência.
7. Rodar um cálculo de teste para um imóvel da UF e verificar a fonte exibida na tela.

## Transparência para o usuário

A calculadora e a página do imóvel exibem:

- Nome da fonte.
- Link da fonte oficial, quando cadastrado.
- Ano e vigência.
- Status de validação.

Isso deixa claro quando o custo é baseado em tabela versionada, tabela legada ou estimativa.

## Cuidados

- Custos cartorários variam por UF, tipo de ato, faixas e atos normativos. O sistema deve ser tratado como estimativa operacional, não como orçamento oficial.
- Antes de decisão de compra, confirme os valores com o cartório competente.
- Não sobrescreva uma tabela validada sem manter histórico de vigência.
