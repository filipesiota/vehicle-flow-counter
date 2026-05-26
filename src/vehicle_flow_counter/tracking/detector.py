"""Detecção de veículos sobre o recorte da ROI (movimento OpenCV e YOLO26)."""

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
        for row in xyxy:
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
                )
            )

        return blobs, mask


class BlobShapeValidator:
    """Filtra contornos por área e aspect ratio (equivalente heurístico ao filtro de classes YOLO)."""

    def __init__(
        self,
        *,
        min_area: int | None = None,
        max_area: int | None = None,
        min_aspect_ratio: float | None = None,
        max_aspect_ratio: float | None = None,
        fragment_min_area: int | None = None,
    ) -> None:
        self._min_area = int(config.MOTION_MIN_BLOB_AREA if min_area is None else min_area)
        self._max_area = int(config.MOTION_MAX_BLOB_AREA if max_area is None else max_area)
        self._min_aspect = float(config.MOTION_MIN_ASPECT_RATIO if min_aspect_ratio is None else min_aspect_ratio)
        self._max_aspect = float(config.MOTION_MAX_ASPECT_RATIO if max_aspect_ratio is None else max_aspect_ratio)
        self._fragment_min_area = int(
            config.MOTION_FRAGMENT_MIN_AREA if fragment_min_area is None else fragment_min_area
        )

    def accepts_fragment(self, contour: np.ndarray) -> bool:
        """Aceita partes pequenas do veículo antes do agrupamento."""
        area = cv2.contourArea(contour)
        if area < self._fragment_min_area:
            return False
        _x, _y, w, h = cv2.boundingRect(contour)
        return w >= 2 and h >= 2

    def accepts(self, contour: np.ndarray) -> bool:
        area = cv2.contourArea(contour)
        if area < self._min_area or area > self._max_area:
            return False

        _x, _y, w, h = cv2.boundingRect(contour)
        if w < 2 or h < 2:
            return False

        aspect = float(w) / float(h)
        return self._min_aspect <= aspect <= self._max_aspect


def _bbox_xywh(contour: np.ndarray) -> tuple[int, int, int, int]:
    x, y, w, h = cv2.boundingRect(contour)
    return int(x), int(y), int(w), int(h)


def _bbox_gap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """Distância mínima entre bordas de dois retângulos (0 se sobrepõem)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = max(0, max(ax, bx) - min(ax + aw, bx + bw))
    dy = max(0, max(ay, by) - min(ay + ah, by + bh))
    return float((dx * dx + dy * dy) ** 0.5)


def _bbox_contains_point(bbox: tuple[int, int, int, int], px: int, py: int) -> bool:
    x, y, w, h = bbox
    return x <= px <= x + w and y <= py <= y + h


def _should_merge_bboxes(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
    *,
    merge_distance_px: float,
) -> bool:
    if _bbox_gap(a, b) <= merge_distance_px:
        return True

    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    acx, acy = ax + aw // 2, ay + ah // 2
    bcx, bcy = bx + bw // 2, by + bh // 2
    return _bbox_contains_point(a, bcx, bcy) or _bbox_contains_point(b, acx, acy)


def _merge_contour_group(contours: list[np.ndarray]) -> np.ndarray:
    points = np.vstack([c.reshape(-1, 2) for c in contours]).astype(np.int32)
    hull = cv2.convexHull(points)
    return hull.reshape(-1, 1, 2)


def _merge_nearby_contours(
    contours: list[np.ndarray],
    *,
    merge_distance_px: float,
) -> list[np.ndarray]:
    """Agrupa fragmentos próximos (rodas, sombra, carroceria) num único contorno."""
    if len(contours) <= 1:
        return contours

    bboxes = [_bbox_xywh(c) for c in contours]
    parent = list(range(len(contours)))

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(contours)):
        for j in range(i + 1, len(contours)):
            if _should_merge_bboxes(bboxes[i], bboxes[j], merge_distance_px=merge_distance_px):
                union(i, j)

    groups: dict[int, list[np.ndarray]] = {}
    for idx, contour in enumerate(contours):
        groups.setdefault(find(idx), []).append(contour)

    return [_merge_contour_group(group) for group in groups.values()]


def _contour_to_blob(contour: np.ndarray, *, ri_w: int, ri_h: int) -> BlobDetection:
    bx, by, bw, bh = cv2.boundingRect(contour)
    bx = int(max(0, min(bx, ri_w - 1)))
    by = int(max(0, min(by, ri_h - 1)))
    bw = int(max(1, min(bw, ri_w - bx)))
    bh = int(max(1, min(bh, ri_h - by)))

    cx = int(round(bx + bw / 2))
    cy = int(round(by + bh / 2))
    cx = max(0, min(cx, ri_w - 1))
    cy = max(0, min(cy, ri_h - 1))

    contour_roi = contour.reshape(-1, 1, 2).astype(np.int32)
    return BlobDetection(cx=cx, cy=cy, bbox_xywh=(bx, by, bw, bh), contour_roi=contour_roi)


class MotionVehicleDetector:
    """
    Detector de veículos por subtração de fundo MOG2 sobre a ROI.

    Gera máscara de movimento, limpa com morfologia, extrai contornos filtrados
    por área/aspect ratio e devolve ``BlobDetection`` compatível com o tracker existente.
    """

    def __init__(
        self,
        *,
        history: int | None = None,
        var_threshold: int | None = None,
        detect_shadows: bool | None = None,
        learning_rate: float | None = None,
        merge_distance_px: float | None = None,
        shape_validator: BlobShapeValidator | None = None,
    ) -> None:
        self._history = int(config.MOTION_BG_HISTORY if history is None else history)
        self._var_threshold = int(config.MOTION_BG_VAR_THRESHOLD if var_threshold is None else var_threshold)
        self._detect_shadows = bool(config.MOTION_DETECT_SHADOWS if detect_shadows is None else detect_shadows)
        self._learning_rate = float(config.MOTION_LEARNING_RATE if learning_rate is None else learning_rate)
        self._merge_distance_px = float(
            config.MOTION_MERGE_DISTANCE_PX if merge_distance_px is None else merge_distance_px
        )

        open_size = max(3, int(config.MOTION_MORPH_OPEN_KERNEL_SIZE) | 1)
        self._open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_size, open_size))

        merge_w = max(3, int(config.MOTION_MORPH_MERGE_KERNEL_WIDTH) | 1)
        merge_h = max(3, int(config.MOTION_MORPH_MERGE_KERNEL_HEIGHT) | 1)
        self._merge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (merge_w, merge_h))

        self._validator = shape_validator or BlobShapeValidator()
        self._bg_subtractor = self._create_subtractor()

    def _create_subtractor(self) -> cv2.BackgroundSubtractorMOG2:
        return cv2.createBackgroundSubtractorMOG2(
            history=self._history,
            varThreshold=self._var_threshold,
            detectShadows=self._detect_shadows,
        )

    def reset(self) -> None:
        """Reinicia o modelo de fundo (necessário ao reiniciar uma sessão de vídeo)."""
        self._bg_subtractor = self._create_subtractor()

    def detect(self, roi_bgr: np.ndarray) -> tuple[list[BlobDetection], np.ndarray]:
        """
        Processa uma ROI em BGR devolvendo detecções e máscara binária (ROI).

        A máscara é uint8 em {0, 255}: branco=região de movimento após limpeza morfológica.
        """
        if roi_bgr.size == 0:
            return [], np.zeros((0, 0), dtype=np.uint8)

        ri_h, ri_w = roi_bgr.shape[:2]
        fg_mask = self._bg_subtractor.apply(roi_bgr, learningRate=self._learning_rate)

        if self._detect_shadows:
            _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        else:
            fg_mask = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)[1]

        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._open_kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._merge_kernel)
        fg_mask = cv2.dilate(fg_mask, self._merge_kernel, iterations=1)

        contours, _hier = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        fragments = [c for c in contours if self._validator.accepts_fragment(c)]
        merged_contours = _merge_nearby_contours(
            fragments,
            merge_distance_px=self._merge_distance_px,
        )

        blobs: list[BlobDetection] = []
        for contour in merged_contours:
            if not self._validator.accepts(contour):
                continue
            blobs.append(_contour_to_blob(contour, ri_w=ri_w, ri_h=ri_h))

        return blobs, fg_mask
