"""Janela raiz CustomTkinter e navegação entre telas."""

from __future__ import annotations

import customtkinter as ctk

from vehicle_flow_counter.config import APP_TITLE


class VehicleFlowCounterApp(ctk.CTk):
    """Shell principal da aplicação — Fase 1: janela vazia, tema por defeito."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(640, 480)
