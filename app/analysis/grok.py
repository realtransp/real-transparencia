"""Cliente da API do Grok (xAI), compatível com o SDK da OpenAI."""
from __future__ import annotations

from functools import lru_cache

from ..config import XAI_API_KEY, XAI_BASE_URL, XAI_MODEL

SYSTEM_PROMPT = (
    "Você é um assistente de transparência pública brasileiro. Explique dados da Câmara "
    "dos Deputados e do TSE em português claro e simples, para qualquer cidadão entender. "
    "Use SOMENTE os números fornecidos no contexto — nunca invente valores. Seja neutro, "
    "factual e conciso. Não emita opinião política. Quando útil, contextualize o que os "
    "números significam na prática."
)


def disponivel() -> bool:
    return bool(XAI_API_KEY)


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    return OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)


def gerar_resumo(prompt: str, max_tokens: int = 500) -> str:
    """Gera um resumo em linguagem simples. Lança se a chave não estiver configurada."""
    if not disponivel():
        raise RuntimeError("XAI_API_KEY não configurada")
    resp = _client().chat.completions.create(
        model=XAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
