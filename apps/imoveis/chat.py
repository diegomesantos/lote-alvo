"""Assistente especialista em leilões de imóveis ancorado num imóvel.

Conversa que responde dúvidas (termos técnicos, regras de leilão, riscos,
sugestões) usando como contexto: os dados do imóvel, a análise jurídica IA já
gerada e o texto de TODOS os documentos enviados (matrícula, edital e demais
anexos, incluindo imagens via OCR).

Provider configurável por variáveis ``AI_CHAT_*`` (cai para a config de análise
jurídica quando não definidas), de forma agnóstica: openai, anthropic, gemini.
"""

import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ChatImovelErro(Exception):
    """Erro operacional esperado ao gerar resposta do chat."""


AI_PROVIDERS_SUPORTADOS = {"openai", "anthropic", "gemini"}

# Ordem de prioridade dos documentos ao montar o contexto (menor = primeiro).
_PRIORIDADE_CATEGORIA = {"matricula": 0, "edital": 1, "processo": 2, "certidao": 3}

_ALIASES_PROVIDER = {
    "open_ai": "openai",
    "claude": "anthropic",
    "anthropic_claude": "anthropic",
    "google": "gemini",
    "google_gemini": "gemini",
}


def _setting_str(nome, default=""):
    return str(getattr(settings, nome, default) or "").strip()


def _provider():
    bruto = _setting_str(
        "AI_CHAT_PROVIDER", _setting_str("AI_LEGAL_ANALYSIS_PROVIDER", "openai")
    ).lower()
    return _ALIASES_PROVIDER.get(bruto, bruto)


def _modelo():
    return _setting_str("AI_CHAT_MODEL", _setting_str("AI_LEGAL_ANALYSIS_MODEL", "gpt-5.5"))


def _api_key(provider):
    chave = _setting_str("AI_CHAT_API_KEY") or _setting_str("AI_LEGAL_ANALYSIS_API_KEY")
    if chave:
        return chave
    if provider == "openai":
        return _setting_str("OPENAI_API_KEY")
    if provider == "anthropic":
        return _setting_str("ANTHROPIC_API_KEY")
    if provider == "gemini":
        return _setting_str("GEMINI_API_KEY", _setting_str("GOOGLE_API_KEY"))
    return ""


def _nome_variavel_chave(provider):
    return {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider, "AI_CHAT_API_KEY")


def _max_output_tokens():
    return int(getattr(settings, "AI_CHAT_MAX_OUTPUT_TOKENS", 1800))


def _limite_contexto_docs():
    return int(getattr(settings, "AI_CHAT_CONTEXT_TEXT_LIMIT", 40000))


def _historico_limite():
    return int(getattr(settings, "AI_CHAT_HISTORY_LIMIT", 16))


def _timeout_segundos():
    # Deve ficar ABAIXO do timeout do gunicorn (--timeout) para a chamada falhar
    # com mensagem amigável em vez de o worker ser morto pelo servidor.
    return int(getattr(settings, "AI_CHAT_TIMEOUT_SECONDS", 100))


# Níveis válidos para reasoning.effort no gpt-5.5: none/low/medium/high/xhigh.
# ("minimal" era do gpt-5 e foi renomeado para "none".)
_GEMINI_THINKING_BUDGET = {
    "none": 0,
    "low": 1024,
    "medium": 4096,
    "high": 12000,
    "xhigh": 24576,
}


def _esforco():
    nivel = _setting_str("AI_CHAT_REASONING_EFFORT", "none").lower()
    if nivel in {"none", "minimal", "minimo", "mínimo", "nenhum"}:
        return "none"
    if nivel in {"baixo"}:
        return "low"
    if nivel in {"alto"}:
        return "high"
    if nivel in {"max", "maximo", "máximo"}:
        return "xhigh"
    if nivel in {"none", "low", "medium", "high", "xhigh"}:
        return nivel
    return "none"


SYSTEM_PROMPT = (
    "Você é um especialista brasileiro em leilões de imóveis (judiciais e "
    "extrajudiciais), arrematação, financiamento e uso de FGTS, execução, "
    "matrícula imobiliária e editais da Caixa. Seu papel é tirar dúvidas, "
    "explicar termos técnicos de forma clara, apontar riscos e responsabilidades "
    "do arrematante e sugerir caminhos práticos de validação e negociação.\n\n"
    "Diretrizes:\n"
    "- Responda em português do Brasil, de forma objetiva e didática.\n"
    "- Para fatos sobre ESTE imóvel, baseie-se apenas no contexto fornecido "
    "(dados, análise jurídica e documentos). Cite o documento/trecho que sustenta "
    "cada afirmação relevante.\n"
    "- Não invente CPF, processo, credor, data, ônus, valor ou responsabilidade. "
    "Se a informação não estiver no contexto, diga que não consta e oriente como "
    "obtê-la.\n"
    "- Para conceitos gerais de leilão/direito, use seu conhecimento, mas deixe "
    "claro quando é orientação geral.\n"
    "- Seja honesto sobre incertezas. Quando algo exigir confirmação documental, "
    "indique isso.\n"
    "- Você NÃO navega na internet nem baixa arquivos. Se um documento (ex.: "
    "edital) não estiver no contexto, diga apenas que ele ainda não está "
    "disponível na análise e oriente o usuário a gerar/atualizar a análise "
    "jurídica do imóvel. Nunca diga que vai tentar acessar links ou baixar PDFs.\n"
    "- Esta conversa é triagem informativa e educativa, NÃO constitui parecer "
    "jurídico nem substitui um advogado."
)


def _texto_util(valor, limite=None):
    texto = " ".join((valor or "").split())
    if limite and len(texto) > limite:
        return texto[:limite].rstrip() + " [TRUNCADO]"
    return texto


def _dados_imovel(imovel, imovel_caixa):
    dados = {
        "endereco": imovel.endereco,
        "cidade": imovel.cidade,
        "estado": imovel.estado,
        "tipo": imovel.get_tipo_imovel_display(),
        "tipo_leilao": imovel.tipo_leilao,
        "data_leilao": imovel.data_leilao.isoformat() if imovel.data_leilao else "",
        "valor_avaliacao": str(imovel.avaliacao or ""),
        "lance": str(imovel.lance or ""),
        "obs": _texto_util(imovel.obs or "", 1200),
    }
    if imovel_caixa:
        dados.update(
            {
                "id_caixa": imovel_caixa.imovel_id_caixa,
                "modalidade": imovel_caixa.modalidade_venda or "",
                "ocupado": bool(imovel_caixa.ocupado),
                "aceita_financiamento": imovel_caixa.pode_financiar,
                "aceita_fgts": imovel_caixa.pode_fgts,
                "percentual_desconto": str(imovel_caixa.percentual_desconto or ""),
            }
        )
    return {k: v for k, v in dados.items() if v not in (None, "", [])}


def _analise_juridica(imovel, imovel_caixa):
    analise = {}
    if imovel_caixa:
        analise = (imovel_caixa.detalhes or {}).get("analise_juridica_ia") or {}
    if not analise.get("resultado"):
        analise = imovel.analise_juridica_ia or {}
    return analise.get("resultado") or {}


def _contexto_documentos(cache):
    limite = _limite_contexto_docs()
    blocos = []
    fontes_com_erro = []

    itens = []
    for entrada in (cache or {}).values():
        texto = (entrada.get("texto") or "").strip()
        nome = entrada.get("nome") or entrada.get("categoria") or "Documento"
        if not texto:
            if entrada.get("erro"):
                fontes_com_erro.append({"documento": nome, "erro": entrada["erro"]})
            continue
        itens.append((entrada.get("categoria") or "", nome, texto))

    # Prioriza matrícula (teor registral, crítico e compacto), depois edital e o
    # restante. Evita que um documento gigante (ex.: edital de 270k chars) consuma
    # todo o orçamento e deixe a matrícula de fora.
    itens.sort(key=lambda it: _PRIORIDADE_CATEGORIA.get(it[0], 9))

    restante = limite
    total = len(itens)
    for indice, (_cat, nome, texto) in enumerate(itens):
        faltam = total - indice
        cota = max(restante // faltam, 1)  # divisão justa do que sobra
        if len(texto) > cota:
            texto = texto[:cota] + "\n[TEXTO TRUNCADO PELO LIMITE OPERACIONAL]"
        blocos.append(f"## Documento: {nome}\n{texto}")
        restante -= len(texto)
        if restante <= 0:
            break

    return "\n\n---\n\n".join(blocos), fontes_com_erro


def _mensagem_contexto(imovel, imovel_caixa, cache):
    contexto_docs, fontes_com_erro = _contexto_documentos(cache)
    partes = [
        "Contexto do imóvel em análise (use como fonte de verdade para perguntas "
        "específicas sobre este caso):",
        "### Dados do imóvel",
        json.dumps(_dados_imovel(imovel, imovel_caixa), ensure_ascii=False),
    ]

    analise = _analise_juridica(imovel, imovel_caixa)
    if analise:
        partes += [
            "### Análise jurídica IA já gerada",
            json.dumps(analise, ensure_ascii=False),
        ]

    if contexto_docs:
        partes += ["### Texto extraído dos documentos", contexto_docs]
    else:
        partes += [
            "### Documentos",
            "Nenhum texto de documento disponível no momento.",
        ]

    if fontes_com_erro:
        partes += [
            "### Documentos sem texto extraível",
            json.dumps(fontes_com_erro, ensure_ascii=False),
        ]

    return "\n\n".join(partes)


def _mensagens_historico(historico):
    """Converte o histórico (lista de dicts role/conteudo) em turnos limpos."""
    limite = _historico_limite()
    recortado = list(historico or [])[-limite:]
    mensagens = []
    for item in recortado:
        role = item.get("role")
        conteudo = (item.get("conteudo") or "").strip()
        if role in ("user", "assistant") and conteudo:
            mensagens.append({"role": role, "content": conteudo})
    return mensagens


# ── Chamadas por provedor ───────────────────────────────────────────────────

def _post_json(url, payload, headers=None, params=None):
    try:
        resposta = requests.post(
            url, headers=headers or {}, params=params or {}, json=payload, timeout=(10, 120)
        )
        resposta.raise_for_status()
    except requests.HTTPError as exc:
        corpo = ""
        if exc.response is not None:
            corpo = (exc.response.text or "")[:500]
        raise ChatImovelErro(f"Falha na API de IA: {corpo or exc}") from exc
    except requests.RequestException as exc:
        raise ChatImovelErro(f"Falha de comunicação com a API de IA: {exc}") from exc
    try:
        return resposta.json()
    except ValueError as exc:
        raise ChatImovelErro("A API de IA retornou resposta sem JSON válido") from exc


def _gerar_openai(mensagens, api_key, modelo):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ChatImovelErro("Pacote openai não instalado") from exc

    client = OpenAI(api_key=api_key, timeout=_timeout_segundos(), max_retries=1)
    try:
        response = client.responses.create(
            model=modelo,
            max_output_tokens=_max_output_tokens(),
            reasoning={"effort": _esforco()},
            input=mensagens,
        )
    except Exception as exc:  # noqa: BLE001
        raise ChatImovelErro(f"Falha na API OpenAI: {exc}") from exc

    texto = getattr(response, "output_text", None)
    if texto:
        return texto.strip()

    partes = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            valor = getattr(content, "text", None)
            if valor:
                partes.append(valor)
    texto = "\n".join(partes).strip()
    if not texto:
        raise ChatImovelErro("A IA não retornou texto")
    return texto


def _gerar_anthropic(system, mensagens, api_key, modelo):
    payload = {
        "model": modelo,
        "max_tokens": _max_output_tokens(),
        "system": system,
        "messages": mensagens,
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": _setting_str("ANTHROPIC_API_VERSION", "2023-06-01"),
        },
    )
    partes = [
        item.get("text", "")
        for item in data.get("content", []) or []
        if item.get("type") == "text"
    ]
    texto = "\n".join(p for p in partes if p).strip()
    if not texto:
        raise ChatImovelErro("A IA não retornou texto (Anthropic)")
    return texto


def _gerar_gemini(system, mensagens, api_key, modelo):
    model_path = modelo if modelo.startswith("models/") else f"models/{modelo}"
    contents = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in mensagens
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": _max_output_tokens(),
            "thinkingConfig": {"thinkingBudget": _GEMINI_THINKING_BUDGET[_esforco()]},
        },
    }
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent",
        payload,
        headers={"content-type": "application/json"},
        params={"key": api_key},
    )
    partes = (
        ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    )
    texto = "\n".join(p.get("text", "") for p in partes if p.get("text")).strip()
    if not texto:
        raise ChatImovelErro("A IA não retornou texto (Gemini)")
    return texto


def _preparar(imovel, imovel_caixa, pergunta, historico, documentos_cache):
    """Valida config e monta as mensagens. Retorna (provider, api_key, modelo, mensagens)."""
    provider = _provider()
    if provider not in AI_PROVIDERS_SUPORTADOS:
        raise ChatImovelErro(
            "Provider de IA não suportado. Use openai, anthropic ou gemini "
            "em AI_CHAT_PROVIDER."
        )

    api_key = _api_key(provider)
    if not api_key:
        raise ChatImovelErro(
            f"Configure AI_CHAT_API_KEY ou {_nome_variavel_chave(provider)} "
            "para usar o assistente."
        )

    modelo = _modelo()
    if not modelo:
        raise ChatImovelErro("Configure AI_CHAT_MODEL com o modelo da IA.")

    pergunta = (pergunta or "").strip()
    if not pergunta:
        raise ChatImovelErro("Escreva uma pergunta.")

    contexto = _mensagem_contexto(imovel, imovel_caixa, documentos_cache)
    historico_msgs = _mensagens_historico(historico)

    # O contexto entra como primeira mensagem de usuário, seguida de um
    # reconhecimento do assistente, para não poluir cada turno do histórico.
    # Manter esse prefixo idêntico entre turnos ativa o cache de prompt do
    # provedor, reduzindo a latência das próximas respostas.
    mensagens = [
        {"role": "user", "content": contexto},
        {
            "role": "assistant",
            "content": "Entendido. Tenho o contexto do imóvel e dos documentos. "
            "Pode perguntar.",
        },
        *historico_msgs,
        {"role": "user", "content": pergunta},
    ]
    return provider, api_key, modelo, mensagens


def responder(imovel, imovel_caixa, pergunta, historico, documentos_cache):
    """Gera a resposta completa do assistente. Lança ChatImovelErro em falhas esperadas."""
    provider, api_key, modelo, mensagens = _preparar(
        imovel, imovel_caixa, pergunta, historico, documentos_cache
    )
    if provider == "openai":
        entrada = [{"role": "system", "content": SYSTEM_PROMPT}, *mensagens]
        return _gerar_openai(entrada, api_key, modelo)
    if provider == "anthropic":
        return _gerar_anthropic(SYSTEM_PROMPT, mensagens, api_key, modelo)
    if provider == "gemini":
        return _gerar_gemini(SYSTEM_PROMPT, mensagens, api_key, modelo)
    raise ChatImovelErro(f"Provider de IA não suportado: {provider}")


def _stream_openai(mensagens, api_key, modelo):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ChatImovelErro("Pacote openai não instalado") from exc

    client = OpenAI(api_key=api_key, timeout=_timeout_segundos(), max_retries=1)
    try:
        stream = client.responses.create(
            model=modelo,
            max_output_tokens=_max_output_tokens(),
            reasoning={"effort": _esforco()},
            input=mensagens,
            stream=True,
        )
        for event in stream:
            if getattr(event, "type", "") == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    yield delta
    except ChatImovelErro:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ChatImovelErro(f"Falha na API OpenAI: {exc}") from exc


def responder_stream(imovel, imovel_caixa, pergunta, historico, documentos_cache):
    """Gera a resposta em pedaços (streaming). Yields trechos de texto.

    Para OpenAI usa streaming nativo (token a token). Para os demais provedores,
    faz a chamada completa e entrega o resultado em um único trecho.
    """
    provider, api_key, modelo, mensagens = _preparar(
        imovel, imovel_caixa, pergunta, historico, documentos_cache
    )
    if provider == "openai":
        entrada = [{"role": "system", "content": SYSTEM_PROMPT}, *mensagens]
        yield from _stream_openai(entrada, api_key, modelo)
    elif provider == "anthropic":
        yield _gerar_anthropic(SYSTEM_PROMPT, mensagens, api_key, modelo)
    elif provider == "gemini":
        yield _gerar_gemini(SYSTEM_PROMPT, mensagens, api_key, modelo)
    else:
        raise ChatImovelErro(f"Provider de IA não suportado: {provider}")
