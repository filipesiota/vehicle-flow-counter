"""Loop principal de tracking com callbacks para UI."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from vehicle_flow_counter import config
from vehicle_flow_counter.domain.models import CountingLine, Roi, TrackingStats, VideoEntry
from vehicle_flow_counter.services.capture_repository import salvar_captura
from vehicle_flow_counter.tracking.detector import BackgroundBlobDetector
from vehicle_flow_counter.tracking.line_crossing import LineCrossingState
from vehicle_flow_counter.tracking.object_tracker import CentroidTracker
from vehicle_flow_counter.tracking.visualizer import build_tracking_view, maybe_scale_for_display
from vehicle_flow_counter.utils.video_utils import video_fps_estimate


class TrackingSession:
    """Orquestra captura OpenCV + visão quando o vídeo já possui ROI/linha válidas."""

    _WINDOW_NAME = "vfc_tracking"

    def __init__(self, entry: VideoEntry, roi: Roi, line: CountingLine) -> None:
        self.entry = entry
        self.roi = roi
        self.line = line

    def run(
        self,
        *,
        stop_event: threading.Event,
        stats_update: Callable[[TrackingStats], None],
        max_preview_side_px: int = 1050,
    ) -> TrackingStats | None:
        """
        Executa até o vídeo terminar ou ``stop_event`` ser sinalizado.

        ``stats_update`` será chamado a partir da worker thread; marshalize atualizações de UI pelo ``after`` no Tk se necessário.
        """
        path = Path(self.entry.video_path)
        stats = TrackingStats(started_at=datetime.now())

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            return None

        fps = video_fps_estimate(cap)
        pause_s = max(1.0 / max(fps, 1e-3), 0.005)

        detector = BackgroundBlobDetector()
        tracker = CentroidTracker()
        crossing_state = LineCrossingState(counting_line=self.line)

        w_frame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h_frame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w_frame <= 0 or h_frame <= 0:
            cap.release()
            return None

        roi = clamp_roi_to_frame(self.roi, w_frame=w_frame, h_frame=h_frame)

        cv2.namedWindow(self._WINDOW_NAME, cv2.WINDOW_NORMAL)
        title_set = getattr(cv2, "setWindowTitle", None)
        window_title = getattr(config, "TRACKING_CV_WINDOW_TITLE", "")
        if callable(title_set) and window_title:
            title_set(self._WINDOW_NAME, window_title)

        try:
            while not stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                roi_slice = crop_roi_safe(frame, roi)
                blobs, fg_mask_roi = detector.detect(roi_slice)
                tracked = tracker.update(blobs)

                for blob in tracked:
                    gx = roi.x + int(blob.cx)
                    gy = roi.y + int(blob.cy)
                    if crossing_state.ingest(blob.vehicle_id, (gx, gy)):
                        stats.vehicles_counted += 1
                        bx, by, bw, bh = blob.bbox_roi
                        gx0 = roi.x + max(0, bx)
                        gy0 = roi.y + max(0, by)

                        gx1 = gx0 + int(bw)
                        gy1 = gy0 + int(bh)

                        gx0 = clamp_int(gx0, 0, frame.shape[1] - 1)
                        gx1 = clamp_int(max(gx0 + 1, gx1), gx0 + 1, frame.shape[1])
                        gy0 = clamp_int(gy0, 0, frame.shape[0] - 1)
                        gy1 = clamp_int(max(gy0 + 1, gy1), gy0 + 1, frame.shape[0])

                        crop = np.ascontiguousarray(frame[gy0:gy1, gx0:gx1, :])
                        if crop.size:
                            salvar_captura(
                                self.entry.captures_dir,
                                vehicle_id=int(blob.vehicle_id),
                                crop_bgr=crop,
                            )

                stats_slice = TrackingStats(started_at=stats.started_at, vehicles_counted=stats.vehicles_counted)
                stats_slice.last_known_ids = {blob.vehicle_id for blob in tracked}
                stats_update(stats_slice)

                vis = build_tracking_view(
                    roi_slice,
                    fg_mask_roi,
                    roi=roi,
                    counting_line_global=self.line,
                    tracks=tracked,
                )
                preview = maybe_scale_for_display(vis, max_side=max_preview_side_px)
                hint = config.TRACKING_CV_WINDOW_HINT
                stripe_h = 44
                cv2.rectangle(
                    preview,
                    (0, max(0, preview.shape[0] - stripe_h)),
                    (preview.shape[1], preview.shape[0]),
                    (24, 24, 24),
                    thickness=-1,
                )
                cv2.putText(
                    preview,
                    hint,
                    (14, preview.shape[0] - 16),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.48,
                    (232, 232, 232),
                    2,
                    lineType=cv2.LINE_AA,
                )
                cv2.imshow(self._WINDOW_NAME, preview)

                delay_ms = max(1, int(round(pause_s * 1000)))
                key = cv2.waitKey(delay_ms) & 0xFF
                # Permite também encerramento por tecla Q dentro da janela OpenCV como atalho.
                if key in (27, ord("q"), ord("Q")):
                    break

                if not self._opencv_window_alive():
                    break

        finally:
            cap.release()
            cv2.destroyWindow(self._WINDOW_NAME)

        return stats

    def _opencv_window_alive(self) -> bool:
        """Retorna ``False`` se o usuário fechou a janela (quando APIs estiverem disponíveis)."""
        prop = getattr(cv2, "WND_PROP_VISIBLE", None)
        if prop is None:
            return True
        try:
            flag = cv2.getWindowProperty(self._WINDOW_NAME, prop)
            return flag >= 0
        except cv2.error:
            return False


def clamp_roi_to_frame(roi: Roi, *, w_frame: int, h_frame: int) -> Roi:
    x = clamp_int(int(roi.x), 0, max(0, w_frame - 1))
    y = clamp_int(int(roi.y), 0, max(0, h_frame - 1))
    wid = clamp_int(int(roi.width), 1, w_frame - x)
    hei = clamp_int(int(roi.height), 1, h_frame - y)
    return Roi(x=x, y=y, width=wid, height=hei)


def crop_roi_safe(full_bgr: np.ndarray, roi: Roi) -> np.ndarray:
    x1 = roi.x + roi.width
    y1 = roi.y + roi.height
    return np.ascontiguousarray(full_bgr[roi.y : y1, roi.x : x1, :])


def clamp_int(val: int, vmin: int, vmax: int) -> int:
    return max(min(int(val), int(vmax)), int(vmin))
