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
