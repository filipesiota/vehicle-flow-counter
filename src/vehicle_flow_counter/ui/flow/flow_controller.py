"""Máquina de estados leve para o wizard guiado: ROI -> linha de contagem."""

from __future__ import annotations

from vehicle_flow_counter import config
from vehicle_flow_counter.domain.models import CountingLine, Roi, VideoEntry
from vehicle_flow_counter.ui.flow.line_selector import run_line_selector
from vehicle_flow_counter.ui.flow.roi_selector import run_roi_selector
from vehicle_flow_counter.utils.video_utils import read_first_frame


class FlowController:
    """
    Orquestra os passos interativos (OpenCV) antes do tracking.

    Ordem atual: ler primeiro frame → selecionar ROI → desenhar linha dentro da ROI.
    Cancelar em qualquer janela (ESC) interrompe todo o fluxo retornando ``None``.
    """

    def run(self, entry: VideoEntry) -> tuple[Roi, CountingLine] | None:
        frame = read_first_frame(entry.video_path)
        roi = run_roi_selector(
            frame,
            window_title=config.FLOW_ROI_WINDOW_TITLE,
            min_dimension=config.ROI_SELECTOR_MIN_SIDE_PX,
            max_side=config.FLOW_SELECTOR_MAX_DISPLAY_SIDE_PX,
        )
        if roi is None:
            return None

        counting_line = run_line_selector(
            frame,
            roi,
            window_title=config.FLOW_LINE_WINDOW_TITLE,
            max_side=config.FLOW_SELECTOR_MAX_DISPLAY_SIDE_PX,
        )
        if counting_line is None:
            return None

        return roi, counting_line
