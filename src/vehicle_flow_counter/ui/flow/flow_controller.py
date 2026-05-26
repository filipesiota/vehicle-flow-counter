"""Máquina de estados leve para o wizard guiado: ROI -> linha de contagem."""

from __future__ import annotations

from vehicle_flow_counter import config
from vehicle_flow_counter.domain.models import CountingLine, Roi, VideoEntry
from vehicle_flow_counter.ui.flow.line_selector import run_line_selector
from vehicle_flow_counter.ui.flow.roi_selector import run_roi_selector
from vehicle_flow_counter.ui.screens.flow_screen import FlowScreen
from vehicle_flow_counter.utils.video_utils import read_first_frame


class FlowController:
    """
    Orquestra os passos interativos antes do tracking.

    Com ``workspace`` embutido na janela principal; sem ``workspace`` usa janelas OpenCV legadas.
    """

    def run(
        self,
        entry: VideoEntry,
        workspace: FlowScreen | None = None,
    ) -> tuple[Roi, CountingLine] | None:
        frame = read_first_frame(entry.video_path)
        max_side = config.FLOW_SELECTOR_MAX_DISPLAY_SIDE_PX
        min_dim = config.ROI_SELECTOR_MIN_SIDE_PX

        if workspace is not None:
            roi = workspace.run_roi_step(frame, min_dimension=min_dim, max_side=max_side)
            if roi is None:
                return None
            counting_line = workspace.run_line_step(frame, roi, max_side=max_side)
            if counting_line is None:
                return None
            return roi, counting_line

        roi = run_roi_selector(
            frame,
            window_title=config.FLOW_ROI_WINDOW_TITLE,
            min_dimension=min_dim,
            max_side=max_side,
        )
        if roi is None:
            return None

        counting_line = run_line_selector(
            frame,
            roi,
            window_title=config.FLOW_LINE_WINDOW_TITLE,
            max_side=max_side,
        )
        if counting_line is None:
            return None

        return roi, counting_line
