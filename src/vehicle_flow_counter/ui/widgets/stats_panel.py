"""Painel lateral atualizado pela sessão de tracking (Tk main thread apenas)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import customtkinter as ctk

from vehicle_flow_counter import config
from vehicle_flow_counter.domain.models import TrackingStats


class StatsPanel(ctk.CTkToplevel):
    """Painel paralelo ao OpenCV mantendo totais atualizados em PT-BR."""

    def __init__(
        self,
        master: Any,
        *,
        stats: TrackingStats,
        on_exit_requested: Callable[[], None],
    ) -> None:
        super().__init__(master)

        self._on_exit = on_exit_requested
        self.title(config.STATS_PANEL_TITLE)
        self.geometry("340x540")
        self.resizable(False, True)
        self.transient(master)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        hero = ctk.CTkFrame(self, fg_color="transparent")
        hero.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(hero, text=config.STATS_PANEL_TITLE, font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w"
        )

        self._started_label = ctk.CTkLabel(hero, text=self._started_text(stats.started_at), anchor="w")
        self._started_label.pack(fill="x", pady=(14, 0))

        separator = ctk.CTkFrame(hero, height=2)
        separator.pack(fill="x", pady=(16, 10))

        ctk.CTkLabel(hero, text=config.STATS_PANEL_TOTAL_LABEL, font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w",
        )
        self._total_label = ctk.CTkLabel(
            hero, text=str(stats.vehicles_counted), font=ctk.CTkFont(size=32, weight="bold")
        )
        self._total_label.pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(hero, text=config.STATS_PANEL_RATE_LABEL, font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w",
            pady=(14, 4),
        )
        self._rate_label = ctk.CTkLabel(hero, text=f"{stats.vehicles_per_minute():.2f}", font=ctk.CTkFont(size=28))
        self._rate_label.pack(anchor="w")

        ids_header = ctk.CTkLabel(
            hero, text="Rastros ativos (IDs)", font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        )

        ids_header.pack(anchor="w", pady=(18, 4))

        self._ids_body = ctk.CTkTextbox(hero, height=115, fg_color=("gray93", "#2B2B2B"))
        self._ids_body.pack(fill="both", expand=True)
        self._ids_body.configure(state="disabled")

        exit_btn = ctk.CTkButton(
            hero,
            text=config.BTN_EXIT_TRACKING_FLOW,
            command=self._handle_exit_clicked,
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        exit_btn.pack(fill="x", pady=(20, 0))

        try:
            self.protocol("WM_DELETE_WINDOW", self._handle_exit_clicked)
        except Exception:
            pass

    def refresh(self, snapshot: TrackingStats, *, clock: datetime | None = None) -> None:
        """Atualização segura somente dentro do loop Tk (use ``after`` a partir da thread worker)."""

        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._started_label.configure(text=self._started_text(snapshot.started_at))

        self._total_label.configure(text=str(snapshot.vehicles_counted))

        rpm = snapshot.vehicles_per_minute(clock)
        self._rate_label.configure(text=f"{rpm:.2f}")

        ids_sorted = sorted(snapshot.last_known_ids)
        if ids_sorted:
            trimmed = ids_sorted[:15]
            extra = "+…" if len(ids_sorted) > len(trimmed) else ""
            blob = ", ".join(str(i) for i in trimmed)
            snippet = (
                "Os seguintes IDs estão ativos nos últimos frames processados:"
                + f"\n\n{blob}{extra}"
            )
        else:
            snippet = (
                "Ainda não detectamos blobs estáveis suficientemente próximos da linha. "
                "Assim que o MOG2 aprender o fundo, os totais aparecem ali em cima."
            )

        self._ids_body.configure(state="normal")
        self._ids_body.delete("1.0", "end")
        self._ids_body.insert("end", snippet + "\n")
        self._ids_body.configure(state="disabled")

        self.update_idletasks()

    def _started_text(self, started_at: datetime) -> str:
        stamp = started_at.strftime("%d/%m/%Y %H:%M:%S")
        return f"{config.STATS_PANEL_STARTED_LABEL} {stamp}"

    def _handle_exit_clicked(self) -> None:
        self._on_exit()
