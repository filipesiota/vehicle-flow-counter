"""Associação frame-a-frame de blobs por IoU + centróide."""

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
    frames_alive: int
    class_id: int


@dataclass
class _TrackState:
    vehicle_id: int
    cx: int
    cy: int
    bbox_roi: tuple[int, int, int, int]
    contour_roi: np.ndarray
    class_id: int
    missing_frames: int = 0
    frames_alive: int = 1


class CentroidTracker:
    """
    Mantém IDs incrementais estáveis associando detecções por IoU e distância de centróide.

    Tracks não associadas por vários frames consecutivos são descartadas (falhas temporárias de detecção).
    """

    def __init__(
        self,
        *,
        max_assoc_distance_px: float | None = None,
        max_misses: int | None = None,
        match_iou_threshold: float | None = None,
    ) -> None:
        distlim = (
            float(config.MAX_ASSOCIATION_DISTANCE_PIXELS)
            if max_assoc_distance_px is None
            else float(max_assoc_distance_px)
        )
        self._max_dist = distlim
        self._max_dist_sq = distlim * distlim
        misses = config.MAX_TRACK_MISSES if max_misses is None else max_misses
        self._max_misses = max(1, int(misses))
        self._match_iou_threshold = (
            float(config.TRACK_MATCH_IOU_THRESHOLD)
            if match_iou_threshold is None
            else float(match_iou_threshold)
        )
        self._tracks: dict[int, _TrackState] = {}
        self._next_id = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, detections: list[BlobDetection]) -> list[TrackedBlob]:
        """Atualiza estados para o frame atual; retorna apenas tracks ativas encontradas."""

        unmatched_indices = set(range(len(detections)))
        matched_track_ids: set[int] = set()

        pairs: list[tuple[float, int, int]] = []
        for di, blob in enumerate(detections):
            for tid, ts in self._tracks.items():
                if not _can_associate(
                    ts,
                    blob,
                    max_dist_sq=self._max_dist_sq,
                    max_dist=self._max_dist,
                    iou_threshold=self._match_iou_threshold,
                ):
                    continue
                score = _association_cost(ts, blob)
                pairs.append((score, di, tid))

        pairs.sort(key=lambda row: row[0])

        for _score, di, tid in pairs:
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
            ts.class_id = blob.class_id
            ts.missing_frames = 0
            ts.frames_alive += 1

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
                class_id=blob.class_id,
                missing_frames=0,
                frames_alive=1,
            )

        return [
            TrackedBlob(
                vehicle_id=st.vehicle_id,
                cx=st.cx,
                cy=st.cy,
                bbox_roi=st.bbox_roi,
                contour_roi=st.contour_roi,
                frames_alive=st.frames_alive,
                class_id=st.class_id,
            )
            for st in self._tracks.values()
        ]


def _bbox_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh

    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = float(iw * ih)
    if inter <= 0.0:
        return 0.0

    union = float(aw * ah + bw * bh) - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def _bbox_scale(bbox: tuple[int, int, int, int]) -> float:
    _x, _y, w, h = bbox
    return float(max(w, h, 1))


def _can_associate(
    track: _TrackState,
    blob: BlobDetection,
    *,
    max_dist_sq: float,
    max_dist: float,
    iou_threshold: float,
) -> bool:
    iou = _bbox_iou(track.bbox_roi, blob.bbox_xywh)
    if iou >= iou_threshold:
        return True

    dx = float(blob.cx - track.cx)
    dy = float(blob.cy - track.cy)
    dist_sq = dx * dx + dy * dy

    scale = max(_bbox_scale(track.bbox_roi), _bbox_scale(blob.bbox_xywh))
    allowed = max(max_dist, scale * 0.55)
    if track.missing_frames > 0:
        allowed *= 1.0 + 0.12 * track.missing_frames

    return dist_sq <= allowed * allowed


def _association_cost(track: _TrackState, blob: BlobDetection) -> float:
    dx = float(blob.cx - track.cx)
    dy = float(blob.cy - track.cy)
    dist = (dx * dx + dy * dy) ** 0.5
    iou = _bbox_iou(track.bbox_roi, blob.bbox_xywh)
    return dist - iou * 250.0
