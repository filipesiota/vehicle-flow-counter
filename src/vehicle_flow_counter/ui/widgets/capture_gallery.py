"""Galeria scrollável com miniaturas das capturas em disco."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image

from vehicle_flow_counter.config import (
    HOME_CAPTURE_CAPTION_VEHICLE,
    HOME_GALLERY_COLS_DEFAULT,
    HOME_GALLERY_THUMB_MAX_PX,
    VEHICLE_SLUG_LABELS_PT,
)
from vehicle_flow_counter.services.capture_repository import listar_capturas


def _caption_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 3:
        vid = parts[-1]
        slug = parts[-2]
        if vid.isdigit():
            label = VEHICLE_SLUG_LABELS_PT.get(slug)
            if label:
                return f"{label} {vid}"
    if "_vehicle_" in stem:
        _, _, vid = stem.rpartition("_vehicle_")
        if vid.isdigit():
            return f"{HOME_CAPTURE_CAPTION_VEHICLE}{vid}"
    return filename


class CaptureGallery(ctk.CTkFrame):
    """
    Lista ``*.jpg`` em um diretório de capturas como miniaturas em colunas fixas.

    Mantém referências a ``CTkImage`` para não serem descartadas pelo GC.
    """

    def __init__(
        self,
        master: Any,
        *,
        thumb_max_px: int = HOME_GALLERY_THUMB_MAX_PX,
        cols: int = HOME_GALLERY_COLS_DEFAULT,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._thumb_max_px = thumb_max_px
        self._cols = max(1, cols)

        self._scroll = ctk.CTkScrollableFrame(self, label_text="", height=280)
        self._scroll.pack(fill="both", expand=True)

        self._image_refs: list[ctk.CTkImage] = []

    def populate_from_dir(self, captures_dir: Path | str | None, *, empty_hint: str) -> None:
        """Carrega miniaturas ou mostra ``empty_hint`` se não houver pasta/arquivos."""
        for child in list(self._scroll.winfo_children()):
            child.destroy()
        self._image_refs.clear()

        if captures_dir is None:
            lbl = ctk.CTkLabel(self._scroll, text=empty_hint, wraplength=380, justify="left")
            lbl.grid(row=0, column=0, sticky="nw", padx=4, pady=8)
            return

        caminho = Path(captures_dir).expanduser().resolve()
        paths = listar_capturas(caminho)

        if not paths:
            lbl = ctk.CTkLabel(self._scroll, text=empty_hint, wraplength=380, justify="left")
            lbl.grid(row=0, column=0, sticky="nw", padx=4, pady=8)
            return

        for idx, path in enumerate(paths):
            row, col = divmod(idx, self._cols)

            celula = ctk.CTkFrame(self._scroll, fg_color=("gray92", "#2a2d2e"), corner_radius=6)
            celula.grid(row=row, column=col, padx=4, pady=4, sticky="nw")

            try:
                pil = Image.open(path).convert("RGB")
                thumb = pil.copy()
                thumb.thumbnail((self._thumb_max_px, self._thumb_max_px), Image.Resampling.LANCZOS)
                w, h = thumb.size
                ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(w, h))
                self._image_refs.append(ctk_img)
                img_label = ctk.CTkLabel(celula, image=ctk_img, text="")
                img_label.pack(padx=6, pady=(6, 2))
                cap = _caption_from_filename(path.name)
                ctk.CTkLabel(celula, text=cap, font=ctk.CTkFont(size=11)).pack(padx=4, pady=(0, 6))
            except OSError:
                # Arquivo ilegível: mostra apenas o nome
                ctk.CTkLabel(celula, text=path.name, wraplength=120, justify="center").pack(
                    padx=8, pady=8
                )
