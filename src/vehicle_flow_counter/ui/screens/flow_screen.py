"""Tela única para ROI, linha de contagem e tracking embutidos na janela principal."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import cv2
import customtkinter as ctk
import numpy as np

from vehicle_flow_counter import config
from vehicle_flow_counter.domain.models import CountingLine, Point2D, Roi, TrackingStats, VideoEntry
from vehicle_flow_counter.services.tracking_session import TrackingSession
from vehicle_flow_counter.ui.flow.line_selector import _clamp_roi_to_frame
from vehicle_flow_counter.ui.widgets.stats_panel import StatsPanel
from vehicle_flow_counter.ui.widgets.video_canvas import VideoCanvas, prepare_display_frame

Phase = Literal["idle", "roi", "line", "tracking"]


@dataclass
class _RoiDragState:
    dragging: bool = False
    ix: int = 0
    iy: int = 0
    x1: int = 0
    y1: int = 0
    finalized: tuple[int, int, int, int] | None = None


class FlowScreen(ctk.CTkFrame):
    """Workspace embutido: wizard ROI/linha e preview de tracking no mesmo shell."""

    def __init__(
        self,
        master: Any,
        *,
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self._on_back = on_back
        self._phase: Phase = "idle"
        self._full_frame: np.ndarray | None = None
        self._display_base: np.ndarray | None = None
        self._disp_scale = 1.0
        self._roi_state = _RoiDragState()
        self._line_points: list[Point2D] = []
        self._active_roi: Roi | None = None
        self._step_result: Any = None
        self._step_done = threading.Event()
        self._mouse_bindings: list[tuple[str, str]] = []
        self._stats_panel: StatsPanel | None = None
        self._tracking_stop: threading.Event | None = None
        self._shortcuts_active = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(header, text=config.BTN_BACK, width=100, command=self._request_back).grid(
            row=0, column=0, sticky="w"
        )
        self._title_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=17, weight="bold"), anchor="w")
        self._title_label.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self._subtitle_label = ctk.CTkLabel(header, text="", anchor="w", wraplength=520)
        self._subtitle_label.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(4, 0))

        canvas_shell = ctk.CTkFrame(self)
        canvas_shell.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        canvas_shell.grid_rowconfigure(0, weight=1)
        canvas_shell.grid_columnconfigure(0, weight=1)

        self._canvas = VideoCanvas(canvas_shell)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self._side_panel = ctk.CTkFrame(self)
        self._side_panel.grid(row=1, column=1, sticky="nsew")

        self._hint_label = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            justify="left",
            wraplength=820,
            font=ctk.CTkFont(size=13),
        )
        self._hint_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _activate_shortcuts(self) -> None:
        if self._shortcuts_active:
            return
        root = self.winfo_toplevel()
        root.bind_all("<Return>", self._on_confirm_key)
        root.bind_all("<KP_Enter>", self._on_confirm_key)
        root.bind_all("<Escape>", self._on_cancel_key)
        root.bind_all("<KeyPress-q>", self._on_cancel_key)
        root.bind_all("<KeyPress-Q>", self._on_cancel_key)
        root.bind_all("<KeyPress-r>", self._on_reset_key)
        root.bind_all("<KeyPress-R>", self._on_reset_key)
        self._shortcuts_active = True

    def _deactivate_shortcuts(self) -> None:
        if not self._shortcuts_active:
            return
        root = self.winfo_toplevel()
        for sequence in (
            "<Return>",
            "<KP_Enter>",
            "<Escape>",
            "<KeyPress-q>",
            "<KeyPress-Q>",
            "<KeyPress-r>",
            "<KeyPress-R>",
        ):
            try:
                root.unbind_all(sequence)
            except Exception:
                pass
        self._shortcuts_active = False

    def reset(self) -> None:
        """Volta ao estado inicial e libera bindings."""
        self._deactivate_shortcuts()
        self._phase = "idle"
        self._full_frame = None
        self._display_base = None
        self._roi_state = _RoiDragState()
        self._line_points.clear()
        self._active_roi = None
        self._step_result = None
        self._step_done.clear()
        self._clear_mouse_bindings()
        self._hide_side_panel()
        self._destroy_stats_panel()
        self._title_label.configure(text="")
        self._subtitle_label.configure(text="")
        self._hint_label.configure(text="")

    def run_roi_step(
        self,
        frame_bgr: np.ndarray,
        *,
        min_dimension: int,
        max_side: int,
    ) -> Roi | None:
        self.reset()
        self._phase = "roi"
        self._full_frame = frame_bgr
        self._display_base, self._disp_scale = prepare_display_frame(
            frame_bgr, max_side=float(max_side)
        )
        self._canvas.set_frame(frame_bgr, max_side=max_side)
        self._title_label.configure(text=config.FLOW_ROI_WINDOW_TITLE)
        self._subtitle_label.configure(text="")
        self._hint_label.configure(
            text=(
                "Arraste um retângulo sobre o frame | ENTER confirma | ESC cancela | "
                f"R limpa | Dimensão mínima: {min_dimension}px"
            )
        )
        self._bind_roi_handlers(min_dimension=min_dimension)
        self._activate_shortcuts()
        self.focus_force()
        return self._wait_for_step()

    def run_line_step(
        self,
        frame_bgr: np.ndarray,
        roi: Roi,
        *,
        max_side: int,
    ) -> CountingLine | None:
        self._phase = "line"
        self._full_frame = frame_bgr
        h_full, w_full = frame_bgr.shape[:2]
        self._active_roi = _clamp_roi_to_frame(roi, w_full=w_full, h_full=h_full)
        self._line_points.clear()
        self._display_base, self._disp_scale = prepare_display_frame(
            frame_bgr, max_side=float(max_side)
        )
        self._canvas.set_frame(frame_bgr, max_side=max_side)
        self._title_label.configure(text=config.FLOW_LINE_WINDOW_TITLE)
        self._subtitle_label.configure(text="")
        self._hint_label.configure(
            text="Dois cliques dentro do retângulo | ENTER confirma | ESC cancela | R redesenha os pontos"
        )
        self._clear_mouse_bindings()
        self._bind_line_handlers()
        self._refresh_line_view()
        self._activate_shortcuts()
        self.focus_force()
        return self._wait_for_step()

    def run_tracking(
        self,
        entry: VideoEntry,
        roi: Roi,
        line: CountingLine,
    ) -> TrackingStats | None:
        self._phase = "tracking"
        self._clear_mouse_bindings()
        self._title_label.configure(text=config.TRACKING_CV_WINDOW_TITLE)
        self._subtitle_label.configure(text=f"Pasta: {entry.slug}")
        self._hint_label.configure(text=config.TRACKING_CV_WINDOW_HINT)

        stop_event = threading.Event()
        self._tracking_stop = stop_event
        baseline = TrackingStats(started_at=datetime.now())
        self._show_stats_panel(stats=baseline, on_exit=stop_event.set)

        def on_stats(update: TrackingStats) -> None:
            if self._stats_panel is not None and self._stats_panel.winfo_exists():
                self._stats_panel.refresh(update)

        def on_frame(preview_bgr: np.ndarray) -> None:
            self._canvas.show_bgr(preview_bgr)

        def pump_ui() -> None:
            try:
                self.update_idletasks()
                self.winfo_toplevel().update_idletasks()
                self.winfo_toplevel().update()
            except Exception:
                return

        session = TrackingSession(entry, roi, line)
        self._activate_shortcuts()
        self.focus_force()
        try:
            return session.run(
                stop_event=stop_event,
                stats_update=on_stats,
                ui_pump=pump_ui,
                frame_sink=on_frame,
            )
        finally:
            self._tracking_stop = None
            self._destroy_stats_panel()

    def _wait_for_step(self) -> Any:
        self._step_result = None
        self._step_done.clear()
        while not self._step_done.is_set():
            try:
                if not self.winfo_exists():
                    return None
                self.update()
            except Exception:
                return None
        return self._step_result

    def _finish_step(self, result: Any) -> None:
        self._deactivate_shortcuts()
        self._step_result = result
        self._step_done.set()

    def _request_back(self) -> None:
        if self._phase == "tracking" and self._tracking_stop is not None:
            self._tracking_stop.set()
            return
        if self._phase in ("roi", "line"):
            self._finish_step(None)
            return
        self._on_back()

    def _on_confirm_key(self, _event: object = None) -> None:
        if self._phase == "roi":
            self._confirm_roi()
        elif self._phase == "line":
            self._confirm_line()

    def _on_cancel_key(self, _event: object = None) -> None:
        if self._phase in ("roi", "line"):
            self._finish_step(None)
        elif self._phase == "tracking" and self._tracking_stop is not None:
            self._tracking_stop.set()

    def _on_reset_key(self, _event: object = None) -> None:
        if self._phase == "roi":
            self._roi_state = _RoiDragState()
            self._refresh_roi_view()
        elif self._phase == "line":
            self._line_points.clear()
            self._refresh_line_view()

    def _bind_roi_handlers(self, *, min_dimension: int) -> None:
        label = self._canvas.image_label

        def on_press(event: Any) -> None:
            xf, yf = self._canvas.display_to_full(event.x, event.y)
            self._roi_state.dragging = True
            self._roi_state.ix = xf
            self._roi_state.iy = yf
            self._roi_state.x1 = xf
            self._roi_state.y1 = yf
            self._roi_state.finalized = None

        def on_motion(event: Any) -> None:
            if not self._roi_state.dragging:
                return
            self._roi_state.x1, self._roi_state.y1 = self._canvas.display_to_full(event.x, event.y)
            self._refresh_roi_view()

        def on_release(event: Any) -> None:
            if not self._roi_state.dragging:
                return
            self._roi_state.dragging = False
            self._roi_state.x1, self._roi_state.y1 = self._canvas.display_to_full(event.x, event.y)
            x0 = min(self._roi_state.ix, self._roi_state.x1)
            y0 = min(self._roi_state.iy, self._roi_state.y1)
            x1 = max(self._roi_state.ix, self._roi_state.x1)
            y1 = max(self._roi_state.iy, self._roi_state.y1)
            self._roi_state.finalized = (x0, y0, x1, y1)
            self._refresh_roi_view()
            self.focus_force()

        self._bind_mouse(label, "<ButtonPress-1>", on_press)
        self._bind_mouse(label, "<B1-Motion>", on_motion)
        self._bind_mouse(label, "<ButtonRelease-1>", on_release)
        self._roi_min_dimension = min_dimension

    def _confirm_roi(self) -> None:
        if self._full_frame is None:
            return
        h_full, w_full = self._full_frame.shape[:2]

        if self._roi_state.finalized is not None:
            fx0, fy0, fx1, fy1 = self._roi_state.finalized
        else:
            fx0 = min(self._roi_state.ix, self._roi_state.x1)
            fy0 = min(self._roi_state.iy, self._roi_state.y1)
            fx1 = max(self._roi_state.ix, self._roi_state.x1)
            fy1 = max(self._roi_state.iy, self._roi_state.y1)

        if fx1 <= fx0 or fy1 <= fy0:
            self._hint_label.configure(
                text="Desenhe um retângulo válido antes de confirmar (arraste com o botão esquerdo)."
            )
            return
        roi_w = fx1 - fx0
        roi_h = fy1 - fy0
        if roi_w < self._roi_min_dimension or roi_h < self._roi_min_dimension:
            self._hint_label.configure(
                text=(
                    f"A ROI é pequena demais ({roi_w}×{roi_h}px). "
                    f"Mínimo: {self._roi_min_dimension}px por lado."
                )
            )
            return
        roi_w = min(roi_w, w_full - fx0)
        roi_h = min(roi_h, h_full - fy0)
        self._finish_step(Roi(x=fx0, y=fy0, width=max(roi_w, 1), height=max(roi_h, 1)))

    def _refresh_roi_view(self) -> None:
        if self._display_base is None:
            return
        vis = self._display_base.copy()
        if self._roi_state.dragging or self._roi_state.finalized is not None:
            xf0 = min(self._roi_state.ix, self._roi_state.x1)
            yf0 = min(self._roi_state.iy, self._roi_state.y1)
            xf1 = max(self._roi_state.ix, self._roi_state.x1)
            yf1 = max(self._roi_state.iy, self._roi_state.y1)
            x0_d, y0_d, x1_d, y1_d = self._canvas.full_to_display_rect(xf0, yf0, xf1, yf1)
            cv2.rectangle(vis, (x0_d, y0_d), (x1_d, y1_d), (60, 200, 255), 2)
        self._canvas.show_bgr(vis)

    def _bind_line_handlers(self) -> None:
        label = self._canvas.image_label

        def on_click(event: Any) -> None:
            if self._active_roi is None or len(self._line_points) >= 2:
                return
            xf, yf = self._canvas.display_to_full(event.x, event.y)
            point = Point2D(x=xf, y=yf)
            if not self._active_roi.contains(point):
                return
            self._line_points.append(point)
            self._refresh_line_view()

        self._bind_mouse(label, "<ButtonPress-1>", on_click)

    def _confirm_line(self) -> None:
        if len(self._line_points) != 2:
            return
        a, b = self._line_points
        self._finish_step(CountingLine(start=a, end=b))

    def _refresh_line_view(self) -> None:
        if self._display_base is None or self._active_roi is None:
            return

        disp = self._display_base.copy()
        disp_scale = self._disp_scale
        roi = self._active_roi
        roi_color = (0, 200, 120)
        line_color = (255, 64, 64)

        roi_rect_d = (
            int(round(roi.x * disp_scale)),
            int(round(roi.y * disp_scale)),
            int(round((roi.x + roi.width) * disp_scale)),
            int(round((roi.y + roi.height) * disp_scale)),
        )

        tint = cv2.addWeighted(disp, 0.35, np.zeros_like(disp), 0.65, 0)
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

        for pf in self._line_points:
            cx = int(round(pf.x * disp_scale))
            cy = int(round(pf.y * disp_scale))
            cv2.circle(canvas, (cx, cy), max(4, int(6 * disp_scale)), (255, 255, 0), -1)

        if len(self._line_points) == 2:
            p0 = (
                int(round(self._line_points[0].x * disp_scale)),
                int(round(self._line_points[0].y * disp_scale)),
            )
            p1 = (
                int(round(self._line_points[1].x * disp_scale)),
                int(round(self._line_points[1].y * disp_scale)),
            )
            cv2.line(canvas, p0, p1, line_color, max(3, int(5 * disp_scale)), lineType=cv2.LINE_AA)

        self._canvas.show_bgr(canvas)

    def _bind_mouse(self, widget: Any, sequence: str, callback: Callable[[Any], None]) -> None:
        widget.bind(sequence, callback)
        self._mouse_bindings.append((widget, sequence))

    def _clear_mouse_bindings(self) -> None:
        for widget, sequence in self._mouse_bindings:
            try:
                widget.unbind(sequence)
            except Exception:
                pass
        self._mouse_bindings.clear()

    def _show_stats_panel(self, *, stats: TrackingStats, on_exit: Callable[[], None]) -> None:
        self._destroy_stats_panel()
        self._side_panel.grid(row=1, column=1, sticky="nsew")
        self._stats_panel = StatsPanel(self._side_panel, stats=stats, on_exit_requested=on_exit)
        self._stats_panel.pack(fill="both", expand=True)

    def _hide_side_panel(self) -> None:
        self._side_panel.grid_remove()

    def _destroy_stats_panel(self) -> None:
        if self._stats_panel is not None:
            try:
                self._stats_panel.destroy()
            except Exception:
                pass
            self._stats_panel = None
        self._hide_side_panel()
