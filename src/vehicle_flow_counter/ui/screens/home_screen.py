"""Tela inicial — lista de vídeos e envio novo."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import customtkinter as ctk

from vehicle_flow_counter.config import (
    BTN_START_VERIFICATION,
    BTN_UPLOAD_NEW_VIDEO,
    HOME_DETAILS_HEADER,
    HOME_DETAILS_NO_SELECTION,
    HOME_GALLERY_EMPTY,
    HOME_GALLERY_HEADER,
    HOME_NO_VIDEOS,
    HOME_SELECTED_LABEL,
    HOME_SELECTED_PATH,
    HOME_VIDEOS_HEADER,
)
from vehicle_flow_counter.domain.models import VideoEntry
from vehicle_flow_counter.services.video_repository import listar_videos
from vehicle_flow_counter.ui.widgets.capture_gallery import CaptureGallery


class HomeScreen(ctk.CTkFrame):
    """Lista vídeos em ``data/videos`` e permite abrir o fluxo de envio."""

    def __init__(
        self,
        master: Any,
        *,
        on_upload_requested: Callable[[], None],
        on_start_verification: Callable[[VideoEntry], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_upload_requested = on_upload_requested
        self._on_start_verification = on_start_verification
        self._selected_slug: str | None = None
        self._selected_entry: VideoEntry | None = None
        self._buttons: dict[str, ctk.CTkButton] = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(header, text=HOME_VIDEOS_HEADER, font=ctk.CTkFont(size=18, weight="bold")).pack(
            side="left"
        )

        ctk.CTkButton(header, text=BTN_UPLOAD_NEW_VIDEO, command=self._on_upload_requested).pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        list_container = ctk.CTkFrame(body)
        list_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._list_body = ctk.CTkScrollableFrame(list_container, label_text="", height=380)
        self._list_body.pack(fill="both", expand=True)

        details = ctk.CTkFrame(body)
        details.grid(row=0, column=1, sticky="nsew")

        details_header_row = ctk.CTkFrame(details, fg_color="transparent")
        details_header_row.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(details_header_row, text=HOME_DETAILS_HEADER, font=ctk.CTkFont(size=15, weight="bold")).pack(
            side="left"
        )

        self._verify_btn = ctk.CTkButton(
            details_header_row,
            text=BTN_START_VERIFICATION,
            width=210,
            command=self._invoke_verification_flow,
            state="disabled",
        )
        self._verify_btn.pack(side="right")

        summary = ctk.CTkFrame(details, fg_color="transparent")
        summary.pack(fill="x", padx=12, pady=(4, 6))

        self._slug_label = ctk.CTkLabel(
            summary,
            text="",
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self._slug_label.pack(fill="x")

        self._path_label = ctk.CTkLabel(
            summary,
            text="",
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self._path_label.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(
            details,
            text=HOME_GALLERY_HEADER,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(fill="x", padx=12, pady=(8, 2))

        self._gallery = CaptureGallery(details)
        self._gallery.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._gallery.populate_from_dir(None, empty_hint=HOME_DETAILS_NO_SELECTION)

    def refresh_video_list(self, *, focus: VideoEntry | None = None) -> None:
        """Recarrega a lista a partir do disco; opcionalmente foca uma entrada pelo ``slug``."""
        for child in self._list_body.winfo_children():
            child.destroy()

        self._buttons.clear()
        self._selected_slug = None
        self._selected_entry = None

        videos = listar_videos()
        if not videos:
            self._verify_btn.configure(state="disabled")
            ctk.CTkLabel(self._list_body, text=HOME_NO_VIDEOS, wraplength=280).pack(pady=20)
            self._clear_details_when_no_library()
            return

        for entry in videos:
            btn = ctk.CTkButton(
                self._list_body,
                text=entry.slug,
                anchor="w",
                height=34,
                command=lambda e=entry: self._select_video(e),
                fg_color="transparent",
                text_color=("gray10", "#DCE4EE"),
                border_width=2,
                border_color=("gray65", "gray40"),
                hover_color=("gray88", "#3B4045"),
            )
            btn.pack(fill="x", pady=(0, 6))
            self._buttons[entry.slug] = btn

        chosen = videos[0]
        if focus is not None:
            for cand in videos:
                if cand.slug == focus.slug:
                    chosen = cand
                    break
        self._select_video(chosen)

    def reload_captures_for_entry(self, tracked: VideoEntry) -> None:
        """Atualiza thumbnails se o vídeo rastreado for o selecionado na home."""
        if self._selected_entry is None or self._selected_entry.slug != tracked.slug:
            return
        ref = tracked.captures_dir.resolve()
        self._gallery.populate_from_dir(ref, empty_hint=HOME_GALLERY_EMPTY)

    def _clear_details_when_no_library(self) -> None:
        self._slug_label.configure(text="")
        self._path_label.configure(text="")
        self._gallery.populate_from_dir(None, empty_hint=HOME_DETAILS_NO_SELECTION)

    def _select_video(self, entry: VideoEntry) -> None:
        self._selected_slug = entry.slug
        self._selected_entry = entry
        self._verify_btn.configure(state="normal")
        self._highlight_selection()

        vp = Path(entry.video_path)
        self._slug_label.configure(text=f"{HOME_SELECTED_LABEL} {entry.slug}")
        self._path_label.configure(text=f"{HOME_SELECTED_PATH}\n{vp}")
        self._gallery.populate_from_dir(entry.captures_dir.resolve(), empty_hint=HOME_GALLERY_EMPTY)

    def _invoke_verification_flow(self) -> None:
        if self._selected_entry is None:
            return
        self._on_start_verification(self._selected_entry)

    def _highlight_selection(self) -> None:
        for slug, btn in self._buttons.items():
            if slug == self._selected_slug:
                btn.configure(
                    fg_color=("#3474A9", "#1F538D"),
                    text_color=("white", "#FAFAFA"),
                    border_width=2,
                    border_color=("#3474A9", "#14375E"),
                    hover_color=("#4487C9", "#2B5EA6"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray10", "#DCE4EE"),
                    border_width=2,
                    border_color=("gray65", "gray40"),
                    hover_color=("gray88", "#3B4045"),
                )
