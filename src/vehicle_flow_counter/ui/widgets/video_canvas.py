"""Exibição de frames BGR dentro da janela principal (sem janelas OpenCV)."""

from __future__ import annotations

from typing import Any

import cv2
import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk


def prepare_display_frame(full_bgr: np.ndarray, *, max_side: float) -> tuple[np.ndarray, float]:
    """Reduz apenas para exibição; ``scale`` mapeia coordenadas de tela -> frame inteiro."""
    h, w = full_bgr.shape[:2]
    longest = max(h, w)
    side = max(float(max_side), 320.0)
    if longest <= side:
        return full_bgr.copy(), 1.0
    scale = side / float(longest)
    disp_w = max(1, int(round(w * scale)))
    disp_h = max(1, int(round(h * scale)))
    return cv2.resize(full_bgr, (disp_w, disp_h), interpolation=cv2.INTER_AREA), scale


class VideoCanvas(ctk.CTkFrame):
    """Mostra um frame BGR redimensionado; eventos de mouse usam pixels da imagem exibida."""

    def __init__(self, master: Any, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._photo: ImageTk.PhotoImage | None = None
        self._disp_scale = 1.0
        self._full_w = 0
        self._full_h = 0

        self._inner = ctk.CTkFrame(self, fg_color="transparent")
        self._inner.pack(expand=True, fill="both")
        self._label = ctk.CTkLabel(self._inner, text="")
        self._label.pack(expand=True)

    @property
    def image_label(self) -> ctk.CTkLabel:
        return self._label

    @property
    def display_scale(self) -> float:
        return self._disp_scale

    @property
    def full_size(self) -> tuple[int, int]:
        return self._full_w, self._full_h

    def set_frame(self, bgr: np.ndarray, *, max_side: int) -> float:
        """Prepara exibição a partir do frame completo; retorna escala display -> frame."""
        self._full_h, self._full_w = bgr.shape[:2]
        display_bgr, self._disp_scale = prepare_display_frame(bgr, max_side=float(max_side))
        self._render_bgr(display_bgr)
        return self._disp_scale

    def show_bgr(self, bgr: np.ndarray, *, max_side: int | None = None) -> float:
        """Atualiza a imagem; com ``max_side`` também reconfigura o mapeamento de coordenadas."""
        if max_side is not None:
            return self.set_frame(bgr, max_side=max_side)
        self._render_bgr(bgr)
        return self._disp_scale

    def _render_bgr(self, bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(pil)
        self._label.configure(image=self._photo)

    def display_to_full(self, x_disp: int, y_disp: int) -> tuple[int, int]:
        xf = int(round(x_disp / self._disp_scale))
        yf = int(round(y_disp / self._disp_scale))
        xf = max(0, min(xf, max(0, self._full_w - 1)))
        yf = max(0, min(yf, max(0, self._full_h - 1)))
        return xf, yf

    def full_to_display_rect(self, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int, int]:
        scale = self._disp_scale
        return (
            int(round(x0 * scale)),
            int(round(y0 * scale)),
            int(round(x1 * scale)),
            int(round(y1 * scale)),
        )
