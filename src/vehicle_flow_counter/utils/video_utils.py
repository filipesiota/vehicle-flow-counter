"""Leituras básicas de vídeo (primeiro frame, metadados) para ferramentas de UI."""

from __future__ import annotations

import time
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


def video_fps_estimate(capture) -> float:
    """
    Extrai FPS declarado pelo arquivo; faz fallback quando o codecs retorna valores absurdos (0 ou >240).
    """
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps != fps or fps < 1e-2 or fps > 240.0:
        return 30.0
    return fps


class RealtimePlaybackClock:
    """
    Relógio de playback: espera só quando estamos adiantados e permite pular frames
    quando o processamento atrasa, mantendo ~1 s de vídeo por 1 s real.
    """

    def __init__(self, fps: float) -> None:
        self._fps = max(float(fps), 1e-3)
        self._started_at = time.perf_counter()

    @property
    def fps(self) -> float:
        return self._fps

    def expected_frame_index(self) -> int:
        elapsed = time.perf_counter() - self._started_at
        return max(0, int(elapsed * self._fps))

    def skip_frames_if_behind(self, capture: cv2.VideoCapture, current_index: int) -> int:
        """Descarta frames não decodificados até alcançar a linha do tempo natural."""
        target = self.expected_frame_index()
        while current_index < target:
            if not capture.grab():
                break
            current_index += 1
        return current_index

    def wait_until_frame_ms(self, frame_index: int) -> int:
        """Milisegundos para ``waitKey`` até o instante natural do frame atual."""
        target_time = frame_index / self._fps
        elapsed = time.perf_counter() - self._started_at
        remaining = target_time - elapsed
        if remaining <= 0.001:
            return 1
        return max(1, int(round(remaining * 1000)))
