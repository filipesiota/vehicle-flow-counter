"""Detecção de veículos com Ultralytics YOLO26 sobre o recorte da ROI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from vehicle_flow_counter import config


@dataclass(slots=True)
class BlobDetection:
    """Detecção em coordenadas do recorte ROI (origin canto superior esquerdo da ROI)."""

    cx: int
    cy: int
    bbox_xywh: tuple[int, int, int, int]  # x, y, w, h relativos à ROI
    contour_roi: np.ndarray  # formato N x 1 x 2, int32, coordenadas na ROI
    class_id: int  # ID COCO (2=car, 3=motorcycle, 5=bus, 7=truck)
    confidence: float


class YoloVehicleDetector:
    """
    Detector de veículos baseado em YOLO26 (COCO: car, motorcycle, bus, truck).

    Executa inferência apenas na ROI recortada; devolve caixas filtradas por confiança
    e classes veiculares, mais uma máscara binária derivada das detecções para visualização.
    """

    def __init__(
        self,
        *,
        model_path: str | None = None,
        confidence: float | None = None,
        imgsz: int | None = None,
        vehicle_class_ids: frozenset[int] | None = None,
        device: str | None = None,
    ) -> None:
        self._model_path = model_path or config.YOLO_MODEL
        self._confidence = float(config.YOLO_CONFIDENCE if confidence is None else confidence)
        self._imgsz = int(config.YOLO_IMGSZ if imgsz is None else imgsz)
        self._vehicle_class_ids = vehicle_class_ids or config.YOLO_VEHICLE_CLASS_IDS
        self._device = self._resolve_device(device)
        self._use_half = self._device.startswith("cuda")
        self._model = YOLO(self._resolve_model_weights())
        self._warmup()

    def _resolve_device(self, device: str | None) -> str:
        if device:
            return device
        configured = config.YOLO_DEVICE.strip()
        if configured:
            return configured
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def _warmup(self) -> None:
        dummy = np.zeros((64, 64, 3), dtype=np.uint8)
        self._model.predict(
            dummy,
            conf=self._confidence,
            classes=sorted(self._vehicle_class_ids),
            imgsz=self._imgsz,
            device=self._device,
            half=self._use_half,
            verbose=False,
        )

    def reset(self) -> None:
        """No-op — YOLO26 não requer estado entre frames (mantido por compatibilidade)."""

    def _resolve_model_weights(self) -> str:
        """Garante pesos em ``data/models/``; baixa automaticamente na primeira execução."""
        target = Path(self._model_path)
        if target.is_file():
            return str(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        weight_name = target.name
        bootstrap = YOLO(weight_name)
        downloaded = Path.cwd() / weight_name
        if downloaded.is_file() and not target.is_file():
            downloaded.replace(target)
            return str(target)

        model_file = getattr(getattr(bootstrap, "model", None), "pt_path", None)
        if model_file and Path(model_file).is_file():
            return str(model_file)

        return weight_name

    def detect(self, roi_bgr: np.ndarray) -> tuple[list[BlobDetection], np.ndarray]:
        """
        Processa uma ROI em BGR devolvendo detecções e máscara binária (ROI).

        A máscara é uint8 em {0, 255}: branco=região ocupada por detecções YOLO.
        """
        if roi_bgr.size == 0:
            return [], np.zeros((0, 0), dtype=np.uint8)

        ri_h, ri_w = roi_bgr.shape[:2]
        mask = np.zeros((ri_h, ri_w), dtype=np.uint8)

        predict_kwargs: dict = {
            "conf": self._confidence,
            "classes": sorted(self._vehicle_class_ids),
            "imgsz": self._imgsz,
            "device": self._device,
            "half": self._use_half,
            "max_det": 32,
            "verbose": False,
        }

        results = self._model.predict(roi_bgr, **predict_kwargs)
        if not results:
            return [], mask

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return [], mask

        blobs: list[BlobDetection] = []
        xyxy = boxes.xyxy.cpu().numpy()
        cls_ids = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        for row, cls_id, conf in zip(xyxy, cls_ids, confidences, strict=True):
            x1, y1, x2, y2 = (float(v) for v in row[:4])
            bx = int(max(0, min(round(x1), ri_w - 1)))
            by = int(max(0, min(round(y1), ri_h - 1)))
            bx2 = int(max(bx + 1, min(round(x2), ri_w)))
            by2 = int(max(by + 1, min(round(y2), ri_h)))
            bw = bx2 - bx
            bh = by2 - by
            if bw < 2 or bh < 2:
                continue

            cx = int(round((bx + bx2) / 2))
            cy = int(round((by + by2) / 2))
            cx = max(0, min(cx, ri_w - 1))
            cy = max(0, min(cy, ri_h - 1))

            contour = np.array(
                [[[bx, by], [bx2, by], [bx2, by2], [bx, by2]]],
                dtype=np.int32,
            )
            cv2.fillPoly(mask, [contour.reshape(-1, 2)], 255)

            blobs.append(
                BlobDetection(
                    cx=cx,
                    cy=cy,
                    bbox_xywh=(bx, by, bw, bh),
                    contour_roi=contour,
                    class_id=int(cls_id),
                    confidence=float(conf),
                )
            )

        return blobs, mask
