"""Seleção de ROI com primeiro frame pausado (arrastar retângulo — OpenCV)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2

from vehicle_flow_counter.domain.models import Roi

# nome interno da janela (ASCII); o título exibido vem do caller via setWindowTitle
_WINDOW = "vfc_roi"


def _prepare_display(full_bgr: np.ndarray, *, max_side: float) -> tuple[np.ndarray, float]:
    """Reduz apenas para exibição; ``scale`` mapeia coordenadas de tela -> frame inteiro."""
    h, w = full_bgr.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return full_bgr, 1.0
    scale = float(max_side) / float(longest)
    disp_w = max(1, int(round(w * scale)))
    disp_h = max(1, int(round(h * scale)))
    return cv2.resize(full_bgr, (disp_w, disp_h), interpolation=cv2.INTER_AREA), scale


def run_roi_selector(full_bgr: np.ndarray, *, window_title: str, min_dimension: int, max_side: int) -> Roi | None:
    """
    Abre uma janela para desenhar a ROI sobre o primeiro frame.

    Shortcuts sobre a imagem: arrastar com o botão esquerdo, ENTER confirmar,
    ESC cancelar, R limpar o retângulo atual.

    Returns:
        ``Roi`` ou ``None`` se cancelado ou inválido.
    """
    display_img, disp_scale = _prepare_display(full_bgr, max_side=max(float(max_side), 320.0))
    h_full, w_full = full_bgr.shape[:2]

    @dataclass
    class _State:
        dragging: bool = False
        ix: int = 0
        iy: int = 0
        x1: int = 0
        y1: int = 0
        finalized: tuple[int, int, int, int] | None = None  # x0,y0,x1,y1 em coords de frame inteiro

    state = _State()

    def _to_full(x_disp: int, y_disp: int) -> tuple[int, int]:
        xf = int(round(x_disp / disp_scale))
        yf = int(round(y_disp / disp_scale))
        xf = max(0, min(xf, w_full - 1))
        yf = max(0, min(yf, h_full - 1))
        return xf, yf

    def mouse_cb(event: int, x: int, y: int, _flags: int, _userdata) -> None:  # noqa: ANN001
        if event == cv2.EVENT_LBUTTONDOWN:
            state.dragging = True
            xf, yf = _to_full(x, y)
            state.ix = xf
            state.iy = yf
            state.x1, state.y1 = xf, yf
            state.finalized = None
        elif event == cv2.EVENT_MOUSEMOVE and state.dragging:
            state.x1, state.y1 = _to_full(x, y)
        elif event == cv2.EVENT_LBUTTONUP and state.dragging:
            state.dragging = False
            state.x1, state.y1 = _to_full(x, y)
            x0 = min(state.ix, state.x1)
            y0 = min(state.iy, state.y1)
            x1 = max(state.ix, state.x1)
            y1 = max(state.iy, state.y1)
            state.finalized = (x0, y0, x1, y1)

    cv2.namedWindow(_WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(_WINDOW, display_img.shape[1], display_img.shape[0])

    title_set = getattr(cv2, "setWindowTitle", None)
    if callable(title_set):
        title_set(_WINDOW, window_title)

    cv2.setMouseCallback(_WINDOW, mouse_cb)

    try:
        while True:
            vis = display_img.copy()
            if state.dragging or state.finalized is not None:
                xf0 = min(state.ix, state.x1)
                yf0 = min(state.iy, state.y1)
                xf1 = max(state.ix, state.x1)
                yf1 = max(state.iy, state.y1)
                r0 = (int(round(xf0 * disp_scale)), int(round(yf0 * disp_scale)))
                r1 = (int(round(xf1 * disp_scale)), int(round(yf1 * disp_scale)))
                cv2.rectangle(vis, r0, r1, (60, 200, 255), 2)

            cv2.imshow(_WINDOW, vis)

            key = cv2.waitKey(15) & 0xFF
            if key in (27,):  # ESC
                return None
            if key in (ord("r"), ord("R")):
                state.finalized = None
                state.dragging = False
                state.ix = state.iy = state.x1 = state.y1 = 0
            if key in (13, 10):  # ENTER
                fx0 = min(state.ix, state.x1)
                fy0 = min(state.iy, state.y1)
                fx1 = max(state.ix, state.x1)
                fy1 = max(state.iy, state.y1)
                if fx1 <= fx0 or fy1 <= fy0:
                    continue
                roi_w = fx1 - fx0
                roi_h = fy1 - fy0
                if roi_w < min_dimension or roi_h < min_dimension:
                    continue
                roi_w = min(roi_w, w_full - fx0)
                roi_h = min(roi_h, h_full - fy0)
                return Roi(x=fx0, y=fy0, width=max(roi_w, 1), height=max(roi_h, 1))
    finally:
        cv2.setMouseCallback(_WINDOW, lambda *_, **__: None)
        cv2.destroyWindow(_WINDOW)
