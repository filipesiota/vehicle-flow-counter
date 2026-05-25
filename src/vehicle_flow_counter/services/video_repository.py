"""Copiar vídeos para ``data/videos/<slug>/`` e listar entradas existentes."""

from __future__ import annotations

import shutil
from pathlib import Path

from vehicle_flow_counter.config import VIDEOS_DIR
from vehicle_flow_counter.domain.models import VideoEntry
from vehicle_flow_counter.utils.filenames import slug_from_original_path, unique_destination_slug


def salvar_video(origem: Path | str) -> VideoEntry:
    """
    Copia um MP4 para ``VIDEOS_DIR/<slug>/video.mp4`` e cria ``capturas/``.

    Raises:
        FileNotFoundError: se ``origem`` não for um arquivo existente.
        ValueError: se a extensão não for ``.mp4``.
    """
    src = Path(origem).expanduser().resolve()
    if not src.is_file():
        msg = f"Arquivo não encontrado: {src}"
        raise FileNotFoundError(msg)
    if src.suffix.lower() != ".mp4":
        raise ValueError("Apenas arquivos MP4 são suportados.")

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    desired = slug_from_original_path(src)
    slug = unique_destination_slug(desired, VIDEOS_DIR)
    dest_dir = VIDEOS_DIR / slug
    dest_dir.mkdir(exist_ok=False)

    dest_video = dest_dir / "video.mp4"
    shutil.copy2(src, dest_video)

    captures_dir = dest_dir / "capturas"
    captures_dir.mkdir(parents=True, exist_ok=True)

    return VideoEntry(slug=slug, video_path=dest_video, captures_dir=captures_dir)


def listar_videos() -> list[VideoEntry]:
    """Lista pastas válidas sob ``VIDEOS_DIR`` que contêm ``video.mp4``."""
    if not VIDEOS_DIR.is_dir():
        return []

    entries: list[VideoEntry] = []
    for child in sorted(VIDEOS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        video_mp4 = child / "video.mp4"
        if not video_mp4.is_file():
            continue
        captures_dir = child / "capturas"
        if not captures_dir.is_dir():
            captures_dir.mkdir(parents=True, exist_ok=True)
        entries.append(
            VideoEntry(
                slug=child.name,
                video_path=video_mp4.resolve(),
                captures_dir=captures_dir.resolve(),
            )
        )

    return entries
