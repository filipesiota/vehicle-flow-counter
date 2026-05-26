"""Persistência de recortes de veículo no disco local."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np


def _captura_sort_key(path: Path) -> tuple[float, str]:
    """
    Extrai ordenação pelo prefixo UNIX (nome ``{unix}_{tipo}_{id}.jpg`` ou legado ``{unix}_vehicle_{id}.jpg``).
    Fallbacks garantem ordenação determinística mesmo com nomes inesperados.
    """
    stem = path.stem
    if "_vehicle_" in stem:
        prefix, _, tail = stem.partition("_vehicle_")
        try:
            return (float(prefix), tail or stem)
        except ValueError:
            pass
    if "_" in stem:
        prefix, _, rest = stem.partition("_")
        try:
            return (float(prefix), rest or stem)
        except ValueError:
            pass
    return (float("inf"), stem.lower())


def listar_capturas(captures_dir: Path | str) -> list[Path]:
    """Lista ``*.jpg``, ordenadas pelo timestamp no nome (cronológico, igual a ``salvar_captura``)."""
    diretorio = Path(captures_dir).expanduser().resolve()
    if not diretorio.is_dir():
        return []

    return sorted(diretorio.glob("*.jpg"), key=_captura_sort_key)


def salvar_captura(
    captures_dir: Path | str,
    *,
    vehicle_id: int,
    crop_bgr: np.ndarray,
    vehicle_class_slug: str = "veiculo",
) -> Path:
    """
    Grava JPEG em ``{captures_dir}/{unix}s_{tipo}_{vehicle_id}.jpg``.

    Raises:
        OSError / cv2.errors: quando o disco estiver bloqueado ou ``imwrite`` falhar.
    """
    dest_parent = Path(captures_dir).expanduser().resolve()
    dest_parent.mkdir(parents=True, exist_ok=True)

    ts = time.time()
    slug = vehicle_class_slug.strip().lower() or "veiculo"
    filename = f"{ts:.6f}_{slug}_{int(vehicle_id)}.jpg"
    target = dest_parent / filename

    ok = cv2.imwrite(str(target), crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        msg = f"Falha ao gravar captura na pasta: {dest_parent}"
        raise OSError(msg)

    return target
