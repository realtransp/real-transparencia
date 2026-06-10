"""Configuração central, lida de variáveis de ambiente.

Local: usa SQLite por padrão para rodar sem instalar Postgres.
Railway: defina DATABASE_URL apontando para o Postgres gerenciado.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Railway injeta DATABASE_URL no plugin Postgres. Sem ele (ou vazio), caímos no SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'resumo_real.db'}"

# Railway/Heroku às vezes entregam "postgres://"; SQLAlchemy quer "postgresql+psycopg://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Camada de análise (LLM). Preferimos Gemini se houver chave; senão xAI/Grok.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
# Modelo usado com busca online (grounding): precisa suportar google_search.
GEMINI_GROUND_MODEL = os.getenv("GEMINI_GROUND_MODEL", "gemini-flash-latest")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4")

# Subsídio mensal bruto do deputado federal (valor fixo, igual para todos).
SUBSIDIO_MENSAL = float(os.getenv("SUBSIDIO_MENSAL", "46366.19"))

# Google AdSense: vazio = sem anúncios. Defina o publisher id (ca-pub-XXXXXXXXXXXXXXXX).
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "")
# Slots de anúncio manuais (criados no painel do AdSense). Vazio = sem aquele anúncio.
ADSENSE_SLOT_FEED = os.getenv("ADSENSE_SLOT_FEED", "")
ADSENSE_SLOT_ARTIGO = os.getenv("ADSENSE_SLOT_ARTIGO", "")
