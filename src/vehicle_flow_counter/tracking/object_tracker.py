"""Associação frame-a-frame de blobs por centróide (distância mínima greedy)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vehicle_flow_counter import config
from vehicle_flow_counter.tracking.detector import BlobDetection


@dataclass(slots=True)
class TrackedBlob:
    """Estado público após atualização incremental do rastreador."""

    vehicle_id: int
    cx: int
    cy: int
    bbox_roi: tuple[int, int, int, int]  # x, y, w, h na ROI
    contour_roi: np.ndarray


@dataclass
class _TrackState:
    vehicle_id: int
    cx: int
    cy: int
    bbox_roi: tuple[int, int, int, int]
    contour_roi: np.ndarray
    missing_frames: int = 0


class CentroidTracker:
    """
    Mantém IDs incrementais estáveis enquanto o centróide se move dentro de uma distância.

    Tracks não associados por vários frames consecutivos são descartadas (lidando com falhas MOG2).
    """

    def __init__(
        self,
        *,
        max_assoc_distance_px: float | None = None,
        max_misses: int = 8,
    ) -> None:
        distlim = (
            float(config.MAX_ASSOCIATION_DISTANCE_PIXELS)
            if max_assoc_distance_px is None
            else float(max_assoc_distance_px)
        )
        self._max_dist_sq = distlim * distlim
        self._max_misses = max(1, max_misses)
        self._tracks: dict[int, _TrackState] = {}
        self._next_id = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, detections: list[BlobDetection]) -> list[TrackedBlob]:
        """Atualiza estados para o frame atual; retorna apenas tracks ativas encontradas."""

        unmatched_indices = set(range(len(detections)))
        matched_track_ids: set[int] = set()

        # Pares ordenados pela distância para matching greedy estável na prática v1.
        pairs: list[tuple[float, int, int]] = []
        for di, blob in enumerate(detections):
            for tid, ts in self._tracks.items():
                dx = float(blob.cx - ts.cx)
                dy = float(blob.cy - ts.cy)
                dsq = dx * dx + dy * dy
                if dsq <= self._max_dist_sq:
                    pairs.append((dsq, di, tid))

        pairs.sort(key=lambda row: row[0])

        for dsq, di, tid in pairs:
            if di not in unmatched_indices:
                continue
            if tid in matched_track_ids:
                continue

            unmatched_indices.discard(di)
            matched_track_ids.add(tid)
            blob = detections[di]
            ts = self._tracks[tid]
            ts.cx = blob.cx
            ts.cy = blob.cy
            ts.bbox_roi = blob.bbox_xywh
            ts.contour_roi = blob.contour_roi
            ts.missing_frames = 0

        stale_tracks = [tid for tid in self._tracks if tid not in matched_track_ids]
        for tid in stale_tracks:
            self._tracks[tid].missing_frames += 1
            if self._tracks[tid].missing_frames >= self._max_misses:
                del self._tracks[tid]

        for di in sorted(unmatched_indices):
            blob = detections[di]
            nid = self._next_id
            self._next_id += 1
            self._tracks[nid] = _TrackState(
                vehicle_id=nid,
                cx=blob.cx,
                cy=blob.cy,
                bbox_roi=blob.bbox_xywh,
                contour_roi=blob.contour_roi,
                missing_frames=0,
            )

        return [
            TrackedBlob(
                vehicle_id=st.vehicle_id,
                cx=st.cx,
                cy=st.cy,
                bbox_roi=st.bbox_roi,
                contour_roi=st.contour_roi,
            )
            for st in self._tracks.values()
        ]
