"""Montagem do quadro combinado mask BGR + marcações e geometria guiada pela ROI."""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from vehicle_flow_counter.config import vehicle_class_label_pt
from vehicle_flow_counter.domain.models import CountingLine, Roi
from vehicle_flow_counter.tracking.object_tracker import TrackedBlob


def build_tracking_view(
    roi_bgr: np.ndarray,
    mask_roi: np.ndarray,
    *,
    roi: Roi,
    counting_line_global: CountingLine,
    tracks: Sequence[TrackedBlob],
) -> np.ndarray:
    """
    Painel combinado ROI-sized em BGR: máscara binária (branco objeto) sobre fundo,

    fusionada discretamente com o recorte para contexto espacial — círculo azul (BGR) no centro,
    rótulo ``{tipo} N`` (ex.: Carro 3) acima da bolha detectada e segmento/limites destacados conforme planejado na Fase 4.
    """

    if mask_roi.ndim != 2 or mask_roi.size == 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    ri_h, ri_w = int(mask_roi.shape[0]), int(mask_roi.shape[1])
    if roi_bgr.shape[:2] != (ri_h, ri_w):
        roi_aligned = cv2.resize(roi_bgr, (ri_w, ri_h), interpolation=cv2.INTER_AREA)
    else:
        roi_aligned = roi_bgr

    mask_u8 = np.asarray(np.clip(mask_roi, 0, 255), dtype=np.uint8)
    mask_bgr = cv2.merge([mask_u8, mask_u8, mask_u8])
    canvas = mask_bgr.copy()

    lx0_g = counting_line_global.start.x
    ly0_g = counting_line_global.start.y
    lx1_g = counting_line_global.end.x
    ly1_g = counting_line_global.end.y

    p0_roi = (float(lx0_g - roi.x), float(ly0_g - roi.y))
    p1_roi = (float(lx1_g - roi.x), float(ly1_g - roi.y))

    clipped = clip_segment_to_rectangle(
        p0_roi,
        p1_roi,
        roi_w=max(roi.width, ri_w),
        roi_h=max(roi.height, ri_h),
    )
    if clipped is not None:
        aa, bb = clipped
        line_thickness = max(2, min(roi.width, roi.height, ri_w, ri_h) // 150)
        p_a = (int(round(aa[0])), int(round(aa[1])))
        p_b = (int(round(bb[0])), int(round(bb[1])))
        cv2.line(canvas, p_a, p_b, (0, 215, 255), line_thickness, lineType=cv2.LINE_AA)
        r_dot = max(4, canvas.shape[0] // 200)
        cv2.circle(canvas, p_a, r_dot, (60, 200, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, p_b, r_dot, (60, 200, 255), -1, lineType=cv2.LINE_AA)

    cv2.rectangle(canvas, (0, 0), (ri_w - 1, ri_h - 1), (96, 96, 96), thickness=1, lineType=cv2.LINE_AA)

    font_scale = float(max(canvas.shape[0], canvas.shape[1])) / 600.0
    font_scale = max(0.45, min(font_scale, 1.05))
    thick_text = max(2, min(int(round(font_scale * 2)), 4))

    for tr in tracks:
        cx_loc = max(0, min(int(tr.cx), ri_w - 1))
        cy_loc = max(0, min(int(tr.cy), ri_h - 1))

        bx, by, bw, bh = tr.bbox_roi
        cv2.rectangle(
            canvas,
            (int(bx), int(by)),
            (int(bx + bw), int(by + bh)),
            (110, 255, 140),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

        radius = max(6, min(ri_w, ri_h) // 40)
        cv2.circle(canvas, (cx_loc, cy_loc), radius, (255, 0, 0), thickness=-1, lineType=cv2.LINE_AA)

        label = f"{vehicle_class_label_pt(tr.class_id)} {tr.vehicle_id}"
        (txt_w, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, font_scale, thick_text)

        txt_x = cx_loc - txt_w // 2
        txt_y = cy_loc - text_height - baseline - 8

        txt_x = max(2, min(txt_x, ri_w - txt_w - 4))
        txt_y = max(text_height + baseline + 4, txt_y)

        cv2.putText(
            canvas,
            label,
            (txt_x, txt_y),
            cv2.FONT_HERSHEY_DUPLEX,
            font_scale,
            (28, 28, 28),
            thick_text + 2,
            lineType=cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            label,
            (txt_x, txt_y),
            cv2.FONT_HERSHEY_DUPLEX,
            font_scale,
            (255, 255, 238),
            thick_text,
            lineType=cv2.LINE_AA,
        )

    fused = cv2.addWeighted(canvas, 0.70, roi_aligned, 0.30, 0.0)
    return fused


def clip_segment_to_rectangle(
    p0: tuple[float, float],
    p1: tuple[float, float],
    *,
    roi_w: int,
    roi_h: int,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Recorta o segmento ao retângulo [0, w–1] x [0, h–1] (Cohen–Sutherland)."""

    x_min, y_min = 0.0, 0.0
    x_max, y_max = float(max(roi_w - 1, 0)), float(max(roi_h - 1, 0))
    x0_, y0_ = p0
    x1_, y1_ = p1

    INSIDE = 0
    LEFT, RIGHT, BOTTOM, TOP = 1, 2, 4, 8

    def _code(xf: float, yf: float) -> int:
        code_val = INSIDE
        if xf < x_min:
            code_val |= LEFT
        elif xf > x_max:
            code_val |= RIGHT
        if yf < y_min:
            code_val |= BOTTOM
        elif yf > y_max:
            code_val |= TOP
        return code_val

    c0 = _code(x0_, y0_)
    c1 = _code(x1_, y1_)

    iterations = 0
    max_iter = 24
    while iterations < max_iter:
        iterations += 1

        if c0 == 0 and c1 == 0:
            return (x0_, y0_), (x1_, y1_)
        if c0 & c1:
            return None

        c_out = c0 if c0 else c1
        xo, yo = 0.0, 0.0

        denom_y = y1_ - y0_
        denom_x = x1_ - x0_

        try:
            if c_out & TOP:
                xo = x0_ + (x1_ - x0_) * (y_max - y0_) / denom_y
                yo = y_max
            elif c_out & BOTTOM:
                xo = x0_ + (x1_ - x0_) * (y_min - y0_) / denom_y
                yo = y_min
            elif c_out & RIGHT:
                yo = y0_ + (y1_ - y0_) * (x_max - x0_) / denom_x
                xo = x_max
            elif c_out & LEFT:
                yo = y0_ + (y1_ - y0_) * (x_min - x0_) / denom_x
                xo = x_min
        except ZeroDivisionError:
            break

        if c_out == c0:
            x0_, y0_ = xo, yo
            c0 = _code(x0_, y0_)
        else:
            x1_, y1_ = xo, yo
            c1 = _code(x1_, y1_)

    return None


def maybe_scale_for_display(canvas_bgr: np.ndarray, *, max_side: int = 950) -> np.ndarray:
    """Redimensiona para caber no monitor sem distorções óbvias."""
    hh, ww = canvas_bgr.shape[:2]
    longest = max(hh, ww, 1)
    if longest <= max_side:
        return canvas_bgr
    scale = float(max_side) / float(longest)
    dw = max(1, int(round(ww * scale)))
    dh = max(1, int(round(hh * scale)))
    return cv2.resize(canvas_bgr, (dw, dh), interpolation=cv2.INTER_AREA)
