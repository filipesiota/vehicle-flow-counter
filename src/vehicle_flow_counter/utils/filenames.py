"""Sanitização de nomes de pasta derivados dos ficheiros de vídeo enviados."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_FALLBACK_SLUG = "video"
_MAX_SLUG_LEN = 80


def slug_from_original_path(original: Path) -> str:
    """Gera um identificador de pasta seguro a partir do nome do ficheiro (sem extensão)."""
    stem = Path(original).stem.strip()
    if not stem:
        return _FALLBACK_SLUG

    normalized = unicodedata.normalize("NFKD", stem)
    ascii_stem = normalized.encode("ascii", "ignore").decode("ascii") or stem
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_stem).strip("_").lower()
    if not slug:
        slug = _FALLBACK_SLUG

    # Evita pasta vazia ou excessivamente longa para o sistema de ficheiros.
    return slug[:_MAX_SLUG_LEN]


def unique_destination_slug(desired_slug: str, videos_dir: Path) -> str:
    """
    Escolhe um nome de pasta único dentro de ``videos_dir``.

    Se ``desired_slug`` já existir, usa sufixos numéricos: ``nome_2``, ``nome_3``, …
    """
    if not (videos_dir / desired_slug).exists():
        return desired_slug

    n = 2
    while True:
        candidate = f"{desired_slug}_{n}"
        if not (videos_dir / candidate).exists():
            return candidate
        n += 1
