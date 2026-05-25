"""Caminhos de dados, textos da UI e constantes globais."""

from __future__ import annotations

from pathlib import Path

# Raiz do projeto (onde está `pyproject.toml`; dois níveis acima deste pacote em `src/`).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Armazenamento local (pastas ignoradas no git).
DATA_DIR = _PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"

# UI — títulos e mensagens reutilizáveis (wizard completo será usado nas fases seguintes).
APP_TITLE = "Contador de fluxo veicular"

# Detector / tracking — valores razoáveis para v1; ajustados nas fases de visão computacional.
MIN_CONTOUR_AREA_PIXELS = 800
MAX_ASSOCIATION_DISTANCE_PIXELS = 80
MORPH_KERNEL_SIZE = (5, 5)
