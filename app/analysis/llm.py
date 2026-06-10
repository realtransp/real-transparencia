"""Camada de LLM para os resumos — Gemini (preferido) ou xAI/Grok, via SDK OpenAI."""
from __future__ import annotations

from functools import lru_cache

from ..config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_GROUND_MODEL,
    GEMINI_MODEL,
    XAI_API_KEY,
    XAI_BASE_URL,
    XAI_MODEL,
)

GEMINI_NATIVE = "https://generativelanguage.googleapis.com/v1beta"

SYSTEM_PROMPT = (
    "Você é um assistente de transparência pública brasileiro. Explique dados da Câmara "
    "dos Deputados e do TSE em português claro e simples, para qualquer cidadão entender. "
    "Use SOMENTE os números fornecidos no contexto — nunca invente valores. Seja neutro, "
    "factual e conciso. Não emita opinião política. Quando útil, contextualize o que os "
    "números significam na prática."
)


def _provider():
    """Retorna (nome, api_key, base_url, model) do provedor ativo, ou None."""
    if GEMINI_API_KEY:
        return ("gemini", GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL)
    if XAI_API_KEY:
        return ("xai", XAI_API_KEY, XAI_BASE_URL, XAI_MODEL)
    return None


def disponivel() -> bool:
    return _provider() is not None


def model_name() -> str:
    p = _provider()
    return p[3] if p else "—"


class RateLimited(RuntimeError):
    """Estourou o limite do tier grátis (429)."""


@lru_cache(maxsize=2)
def _client(api_key: str, base_url: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url)


def gerar_resumo(prompt: str, max_tokens: int = 500, grounded: bool = False) -> str:
    p = _provider()
    if not p:
        raise RuntimeError("nenhum provedor de IA configurado")
    if grounded and p[0] == "gemini":
        return _gemini_grounded(prompt, max_tokens)
    _, key, base, model = p
    try:
        resp = _client(key, base).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        if "429" in str(exc) or "quota" in str(exc).lower() or "rate" in str(exc).lower():
            raise RateLimited(str(exc)) from exc
        raise
    return (resp.choices[0].message.content or "").strip()


def _gemini_grounded(prompt: str, max_tokens: int) -> str:
    """Chamada nativa do Gemini com Google Search (busca online) para checar fatos."""
    import httpx

    url = f"{GEMINI_NATIVE}/models/{GEMINI_GROUND_MODEL}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    r = httpx.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=90,
    )
    if r.status_code == 429:
        raise RateLimited(r.text)
    r.raise_for_status()
    parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()
