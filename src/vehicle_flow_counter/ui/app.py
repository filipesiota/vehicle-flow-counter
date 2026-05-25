"""Janela raiz CustomTkinter e navegação entre telas."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from vehicle_flow_counter.config import (
    APP_TITLE,
    FLOW_CONFIGURE_ERROR_TITLE,
    FLOW_CONFIGURED_MESSAGE,
    FLOW_CONFIGURED_TITLE,
)
from vehicle_flow_counter.domain.models import VideoEntry
from vehicle_flow_counter.ui.flow.flow_controller import FlowController
from vehicle_flow_counter.ui.screens.home_screen import HomeScreen
from vehicle_flow_counter.ui.screens.upload_screen import UploadScreen


class VehicleFlowCounterApp(ctk.CTk):
    """Shell principal — home com lista de vídeos e tela de envio."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(640, 480)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._shell = ctk.CTkFrame(self, fg_color="transparent")
        self._shell.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self._shell.grid_columnconfigure(0, weight=1)
        self._shell.grid_rowconfigure(0, weight=1)

        self._home = HomeScreen(
            self._shell,
            on_upload_requested=self._show_upload,
            on_start_verification=self._start_flow_wizard,
        )
        self._upload = UploadScreen(
            self._shell,
            on_back=self._show_home,
            on_ready_for_flow=self._finish_upload_then_wizard,
        )

        self._home.grid(row=0, column=0, sticky="nsew")

        self._home.refresh_video_list()

    def _show_upload(self) -> None:
        self._upload.reset_session()
        self._home.grid_remove()
        self._upload.grid(row=0, column=0, sticky="nsew")

    def _show_home(self, *, focus: VideoEntry | None = None) -> None:
        self._upload.grid_remove()
        self._upload.reset_session()
        self._home.grid(row=0, column=0, sticky="nsew")
        self._home.refresh_video_list(focus=focus)

    def _finish_upload_then_wizard(self, saved: VideoEntry) -> None:
        """Volta ao home já com vídeo novo e abre ROI/linha (OpenCV)."""
        self._show_home(focus=saved)
        self.after(150, lambda entry=saved: self._start_flow_wizard(entry))

    def _start_flow_wizard(self, entry: VideoEntry) -> None:
        """Executa seleção ROI + linha; cancelar (ESC) apenas fecha sem mensagem."""
        try:
            controller = FlowController()
            outcome = controller.run(entry)
        except ValueError as exc:
            messagebox.showerror(FLOW_CONFIGURE_ERROR_TITLE, str(exc))
            return

        if outcome is None:
            return

        _roi, _line = outcome  # placeholders para a Fase 4 (sessão de tracking)
        messagebox.showinfo(FLOW_CONFIGURED_TITLE, FLOW_CONFIGURED_MESSAGE)
