"""Leituras básicas de vídeo (primeiro frame, metadados) para ferramentas de UI."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def read_first_frame(video_path: Path | str) -> np.ndarray:
    """
    Retorna o primeiro frame em BGR (``numpy.uint8``, shape ``H x W x 3``).

    Raises:
        ValueError: se o arquivo não puder ser aberto ou não houver frame legível.
    """
    src = Path(video_path)
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        msg = f"Não foi possível abrir o vídeo: {src}"
        raise ValueError(msg)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        msg = "Nenhum frame pôde ser lido neste arquivo."
        raise ValueError(msg)
    return np.asarray(frame, dtype=np.uint8)
