"""Seleção da linha de contagem por dois pontos dentro da ROI (OpenCV)."""

from __future__ import annotations

import cv2
import numpy as np

from vehicle_flow_counter.domain.models import CountingLine, Point2D, Roi

_WINDOW = "vfc_line"


def run_line_selector(full_bgr: np.ndarray, roi: Roi, *, window_title: str, max_side: int) -> CountingLine | None:
    """
    Escolha de dois pontos **em coordenadas do frame inteiro**, obrigatoriamente
    dentro da ROI (limites inclusive/exclusivos de ``Roi.contains``).

    ENTER confirma (com dois pontos válidos); ESC cancela; R redefine os dois pontos.
    """
    h_full, w_full = full_bgr.shape[:2]
    roi = _clamp_roi_to_frame(roi, w_full=w_full, h_full=h_full)

    def _prepare(full: np.ndarray) -> tuple[np.ndarray, float]:
        hh, ww = full.shape[:2]
        longest = max(hh, ww)
        mx = float(max(max_side, 320))
        if longest <= mx:
            return full.copy(), 1.0
        scale = mx / float(longest)
        dw = max(1, int(round(ww * scale)))
        dh = max(1, int(round(hh * scale)))
        return cv2.resize(full, (dw, dh), interpolation=cv2.INTER_AREA), scale

    disp, disp_scale = _prepare(full_bgr)

    pts_full: list[Point2D] = []

    def _full_from_disp(x: int, y: int) -> Point2D:
        xf = int(round(x / disp_scale))
        yf = int(round(y / disp_scale))
        xf = max(0, min(xf, w_full - 1))
        yf = max(0, min(yf, h_full - 1))
        return Point2D(x=xf, y=yf)

    def mouse_cb(event: int, x: int, y: int, _flags: int, _userdata) -> None:  # noqa: ANN001
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if len(pts_full) >= 2:
            return
        pf = _full_from_disp(x, y)
        if not roi.contains(pf):
            return
        pts_full.append(pf)

    cv2.namedWindow(_WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(_WINDOW, disp.shape[1], disp.shape[0])
    title_set = getattr(cv2, "setWindowTitle", None)
    if callable(title_set):
        title_set(_WINDOW, window_title)
    cv2.setMouseCallback(_WINDOW, mouse_cb)

    roi_color = (0, 200, 120)
    line_color = (255, 64, 64)

    try:
        while True:
            vis = disp.copy()
            roi_rect_d = (
                int(round(roi.x * disp_scale)),
                int(round(roi.y * disp_scale)),
                int(round((roi.x + roi.width) * disp_scale)),
                int(round((roi.y + roi.height) * disp_scale)),
            )

            tint = cv2.addWeighted(vis, 0.35, np.zeros_like(vis), 0.65, 0)
            x0_d, y0_d, x1_d, y1_d = roi_rect_d
            dh_disp, dw_disp = disp.shape[:2]
            x0_d = max(0, min(x0_d, dw_disp - 1))
            y0_d = max(0, min(y0_d, dh_disp - 1))
            x1_d = max(0, min(x1_d, dw_disp))
            y1_d = max(0, min(y1_d, dh_disp))
            x1_d = max(x1_d, x0_d + 1)
            y1_d = max(y1_d, y0_d + 1)
            roi_slice = tint[y0_d:y1_d, x0_d:x1_d]
            roi_src = disp[y0_d:y1_d, x0_d:x1_d]
            if roi_slice.shape == roi_src.shape and roi_src.size != 0:
                roi_slice[:, :] = roi_src

            cv2.rectangle(tint, (x0_d, y0_d), (x1_d, y1_d), roi_color, 2)
            canvas = tint

            for i, pf in enumerate(pts_full):
                cx = int(round(pf.x * disp_scale))
                cy = int(round(pf.y * disp_scale))
                cv2.circle(canvas, (cx, cy), max(4, int(6 * disp_scale)), (255, 255, 0), -1)

            if len(pts_full) == 2:
                p0 = (int(round(pts_full[0].x * disp_scale)), int(round(pts_full[0].y * disp_scale)))
                p1 = (int(round(pts_full[1].x * disp_scale)), int(round(pts_full[1].y * disp_scale)))
                cv2.line(canvas, p0, p1, line_color, max(3, int(5 * disp_scale)), lineType=cv2.LINE_AA)

            cv2.imshow(_WINDOW, canvas)
            key = cv2.waitKey(15) & 0xFF
            if key in (27,):
                return None
            if key in (ord("r"), ord("R")):
                pts_full.clear()
            if key in (13, 10):
                if len(pts_full) != 2:
                    continue
                a, b = pts_full
                return CountingLine(start=a, end=b)
    finally:
        cv2.setMouseCallback(_WINDOW, lambda *_, **__: None)
        cv2.destroyWindow(_WINDOW)


def _clamp_roi_to_frame(roi: Roi, *, w_full: int, h_full: int) -> Roi:
    x = max(0, min(roi.x, max(0, w_full - 1)))
    y = max(0, min(roi.y, max(0, h_full - 1)))
    w = max(1, min(roi.width, w_full - x))
    h = max(1, min(roi.height, h_full - y))
    return Roi(x=x, y=y, width=w, height=h)
