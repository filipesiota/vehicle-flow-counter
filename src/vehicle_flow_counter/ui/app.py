"""Janela raiz CustomTkinter e navegação entre telas."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from vehicle_flow_counter.config import (
    APP_TITLE,
    FLOW_CONFIGURE_ERROR_TITLE,
    TRACKING_OPEN_FAILED_MESSAGE,
    TRACKING_OPEN_FAILED_TITLE,
)
from vehicle_flow_counter.domain.models import VideoEntry
from vehicle_flow_counter.services.capture_repository import limpar_capturas
from vehicle_flow_counter.ui.flow.flow_controller import FlowController
from vehicle_flow_counter.ui.screens.flow_screen import FlowScreen
from vehicle_flow_counter.ui.screens.home_screen import HomeScreen
from vehicle_flow_counter.ui.screens.upload_screen import UploadScreen


class VehicleFlowCounterApp(ctk.CTk):
    """Shell principal — home, envio e fluxo de verificação na mesma janela."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(760, 520)

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
        self._flow = FlowScreen(self._shell, on_back=self._show_home)

        self._home.grid(row=0, column=0, sticky="nsew")
        self._home.refresh_video_list()

        self._flow_active = False

    def _safe_reset_upload(self) -> None:
        try:
            if self._upload.winfo_exists():
                self._upload.reset_session()
        except Exception:
            pass

    def _hide_all_screens(self) -> None:
        self._home.grid_remove()
        self._upload.grid_remove()
        self._flow.grid_remove()

    def _show_upload(self) -> None:
        self._safe_reset_upload()
        self._hide_all_screens()
        self._upload.grid(row=0, column=0, sticky="nsew")

    def _show_home(self, *, focus: VideoEntry | None = None) -> None:
        self._safe_reset_upload()
        self._flow.reset()
        self._hide_all_screens()
        self._home.grid(row=0, column=0, sticky="nsew")
        self._home.refresh_video_list(focus=focus)

    def _show_flow(self) -> None:
        self._hide_all_screens()
        self._flow.grid(row=0, column=0, sticky="nsew")
        self._flow.focus_set()

    def _finish_upload_then_wizard(self, saved: VideoEntry) -> None:
        """Abre o fluxo embutido logo após o envio."""
        self.after(150, lambda entry=saved: self._start_flow_wizard(entry))

    def _start_flow_wizard(self, entry: VideoEntry) -> None:
        """ROI + linha + tracking na mesma tela; cancelar (ESC) volta ao home."""
        if self._flow_active:
            return

        self._flow_active = True
        try:
            limpar_capturas(entry.captures_dir)
            self._show_flow()
            self.update_idletasks()
            if not self._flow.winfo_ismapped():
                return

            try:
                controller = FlowController()
                outcome = controller.run(entry, self._flow)
            except ValueError as exc:
                messagebox.showerror(FLOW_CONFIGURE_ERROR_TITLE, str(exc))
                self._show_home(focus=entry)
                return

            if outcome is None:
                self._show_home(focus=entry)
                return

            roi, line = outcome
            snapshot = self._flow.run_tracking(entry, roi=roi, line=line)

            self._show_home(focus=entry)
            if snapshot is None:
                messagebox.showerror(TRACKING_OPEN_FAILED_TITLE, TRACKING_OPEN_FAILED_MESSAGE)
            else:
                self._home.reload_captures_for_entry(entry)
        finally:
            self._flow_active = False
