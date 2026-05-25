"""Janela raiz CustomTkinter e navegação entre telas."""

from __future__ import annotations

import customtkinter as ctk

from vehicle_flow_counter.config import APP_TITLE
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

        self._home = HomeScreen(self._shell, on_upload_requested=self._show_upload)
        self._upload = UploadScreen(self._shell, on_back=self._show_home, on_ready_for_flow=self._on_upload_complete)

        self._home.grid(row=0, column=0, sticky="nsew")

        self._home.refresh_video_list()

    def _show_upload(self) -> None:
        self._upload.reset_session()
        self._home.grid_remove()
        self._upload.grid(row=0, column=0, sticky="nsew")

    def _show_home(self) -> None:
        self._upload.grid_remove()
        self._upload.reset_session()
        self._home.grid(row=0, column=0, sticky="nsew")
        self._home.refresh_video_list()

    def _on_upload_complete(self) -> None:
        """Após cópia com sucesso: o usuário pediu iniciar verificação (wizard na Fase 3)."""
        self._show_home()
