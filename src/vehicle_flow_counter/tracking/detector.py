"""Detecção de blobs em movimento (MOG2 + morfologia) sobre o recorte da ROI."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from vehicle_flow_counter import config


@dataclass(slots=True)
class BlobDetection:
    """Detecção em coordenadas do recorte ROI (origin canto superior esquerdo da ROI)."""

    cx: int
    cy: int
    bbox_xywh: tuple[int, int, int, int]  # x, y, w, h relativos à ROI
    contour_roi: np.ndarray  # formato N x 1 x 2, int32, coordenadas na ROI


class BackgroundBlobDetector:
    """
    Subtração de fundo MOG2 aplicada apenas à região recortada (ROI).

    A morfologia reduz ruído; apenas contornos externos acima da área mínima são retornados.
    """

    def __init__(
        self,
        *,
        min_area: int | None = None,
        morph_kernel_size: tuple[int, int] | None = None,
        mog2_variant_threshold: float = 16.0,
        mog2_detect_shadows: bool = False,
    ) -> None:
        min_area_val = config.MIN_CONTOUR_AREA_PIXELS if min_area is None else min_area
        self._min_area = max(1, int(min_area_val))
        ks = morph_kernel_size or config.MORPH_KERNEL_SIZE
        self._kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, ks)
        self._kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, ks)

        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=mog2_detect_shadows,
            varThreshold=mog2_variant_threshold,
        )

    def reset(self) -> None:
        """Recria o subtrator (útil ao reiniciar leitura do vídeo desde o frame 0)."""
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False,
            varThreshold=16.0,
        )

    def detect(self, roi_bgr: np.ndarray) -> tuple[list[BlobDetection], np.ndarray]:
        """
        Processa uma ROI em BGR devolvendo detecções e máscara binária foreground (ROI).

        A máscara é uint8 em {0, 255}: branco=frente planeada após threshold+morfologia.
        """
        if roi_bgr.size == 0:
            return [], np.zeros((0, 0), dtype=np.uint8)

        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        fg_raw = self._subtractor.apply(gray, learningRate=-1)

        # MOG2 com sombras pode marcar sombras como 127; binarização simples.
        _, binary = cv2.threshold(fg_raw, 127, 255, cv2.THRESH_BINARY)
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._kernel_open, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self._kernel_close, iterations=1)

        contours, _hier = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        blobs: list[BlobDetection] = []
        ri_h, ri_w = closed.shape[:2]
        for c in contours:
            area = float(cv2.contourArea(c))
            if area < self._min_area:
                continue

            bx, by, bw, bh = cv2.boundingRect(c)
            if bw < 2 or bh < 2:
                continue

            moments = cv2.moments(c)
            denom = moments["m00"]
            if denom <= 1e-6:
                continue
            cx_loc = int(moments["m10"] / denom)
            cy_loc = int(moments["m01"] / denom)
            cx_loc = max(0, min(cx_loc, ri_w - 1))
            cy_loc = max(0, min(cy_loc, ri_h - 1))

            c_loc = np.asarray(c, dtype=np.int32)

            blobs.append(
                BlobDetection(
                    cx=cx_loc,
                    cy=cy_loc,
                    bbox_xywh=(bx, by, bw, bh),
                    contour_roi=c_loc,
                )
            )

        return blobs, closed
