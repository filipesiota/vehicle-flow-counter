"""Tela de envio — escolha de MP4, barra durante cópia, botão para iniciar verificação."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog
from tkinter.messagebox import showerror

import customtkinter as ctk

from vehicle_flow_counter.config import (
    BTN_BACK,
    BTN_CHANGE_FILE,
    BTN_CONFIRM_SEND,
    BTN_SELECT_FILE,
    BTN_START_VERIFICATION,
    UPLOAD_DIALOG_FILETYPES,
    UPLOAD_DIALOG_TITLE,
    UPLOAD_MP4_REQUIRED,
    UPLOAD_SAVE_ERROR,
    UPLOAD_SUCCESS,
    UPLOAD_COPYING_LABEL,
    UPLOAD_SELECTED_NONE,
    UPLOAD_TITLE,
)
from vehicle_flow_counter.services.video_repository import salvar_video


class UploadScreen(ctk.CTkFrame):
    """Permite seleção de um MP4 e cópia assíncrona para ``data/videos``."""

    def __init__(
        self,
        master,
        *,
        on_back: Callable[[], None],
        on_ready_for_flow: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_back = on_back
        self._on_ready_for_flow = on_ready_for_flow

        self._selected_path: Path | None = None
        self._copied_ready = False
        self._busy = threading.Event()

        ctk.CTkLabel(self, text=UPLOAD_TITLE, font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", pady=(0, 16)
        )

        self._name_label = ctk.CTkLabel(self, text=UPLOAD_SELECTED_NONE, anchor="w", wraplength=640)
        self._name_label.pack(fill="x", pady=(0, 8))

        btns_row = ctk.CTkFrame(self, fg_color="transparent")
        btns_row.pack(fill="x", pady=(0, 16))

        self._pick_btn = ctk.CTkButton(btns_row, text=BTN_SELECT_FILE, command=self._open_dialog)
        self._pick_btn.pack(side="left", padx=(0, 8))

        self._change_btn = ctk.CTkButton(
            btns_row, text=BTN_CHANGE_FILE, command=self._open_dialog, state="disabled"
        )
        self._change_btn.pack(side="left", padx=(0, 8))

        self._confirm_btn = ctk.CTkButton(btns_row, text=BTN_CONFIRM_SEND, command=self._confirm_send)
        self._confirm_btn.pack(side="left")

        self._progress = ctk.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")
        self._progress.pack(fill="x", pady=(0, 8))
        self._progress.pack_forget()

        self._status_label = ctk.CTkLabel(self, text="", anchor="w")
        self._status_label.pack(fill="x")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=(24, 0))

        self._flow_btn = ctk.CTkButton(
            footer, text=BTN_START_VERIFICATION, command=self._finish_and_go_home, state="disabled"
        )
        self._flow_btn.pack(side="right", padx=(8, 0))

        ctk.CTkButton(footer, text=BTN_BACK, command=self._on_back_requested).pack(side="right")

    def reset_session(self) -> None:
        """Repor o estado antes de mostrar esta tela de novo."""
        self._busy.clear()
        self._selected_path = None
        self._copied_ready = False

        self._name_label.configure(text=UPLOAD_SELECTED_NONE)
        self._status_label.configure(text="")

        self._pick_btn.configure(state="normal")
        self._change_btn.configure(state="disabled")
        self._confirm_btn.configure(state="disabled")
        self._flow_btn.configure(state="disabled")

        self._progress.stop()
        self._progress.pack_forget()

    def _on_back_requested(self) -> None:
        if self._busy.is_set():
            return
        self.reset_session()
        self._on_back()

    def _open_dialog(self) -> None:
        if self._busy.is_set():
            return
        filename = filedialog.askopenfilename(
            title=UPLOAD_DIALOG_TITLE,
            filetypes=UPLOAD_DIALOG_FILETYPES,
        )
        if not filename:
            return

        candidate = Path(filename)
        if candidate.suffix.lower() != ".mp4":
            showerror("Erro", UPLOAD_MP4_REQUIRED)
            return

        self._selected_path = candidate
        display = candidate.name
        self._name_label.configure(text=display)

        self._change_btn.configure(state="normal")
        self._confirm_btn.configure(state="normal")
        self._flow_btn.configure(state="disabled")

        self._copied_ready = False
        self._status_label.configure(text="")

    def _confirm_send(self) -> None:
        if self._selected_path is None or self._busy.is_set():
            return

        path = self._selected_path
        self._busy.set()

        self._pick_btn.configure(state="disabled")
        self._change_btn.configure(state="disabled")
        self._confirm_btn.configure(state="disabled")

        self._progress.pack(fill="x", pady=(0, 8))
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._status_label.configure(text=UPLOAD_COPYING_LABEL)

        threading.Thread(target=self._copy_worker, args=(path,), daemon=True).start()

    def _copy_worker(self, path: Path) -> None:
        try:
            salvar_video(path)
            ok = True
            err_msg: str | None = None
        except (OSError, ValueError) as exc:
            ok = False
            err_msg = str(exc)

        self.after(0, lambda: self._on_copy_finished(ok=ok, detail=err_msg))

    def _on_copy_finished(self, *, ok: bool, detail: str | None) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._busy.clear()

        if ok:
            self._copied_ready = True
            self._pick_btn.configure(state="disabled")
            self._change_btn.configure(state="disabled")
            self._confirm_btn.configure(state="disabled")
            self._flow_btn.configure(state="normal")
            self._status_label.configure(text=UPLOAD_SUCCESS)
        else:
            self._copied_ready = False
            self._pick_btn.configure(state="normal")
            self._change_btn.configure(state="normal")
            self._confirm_btn.configure(state="normal")
            self._flow_btn.configure(state="disabled")
            hint = UPLOAD_SAVE_ERROR + (f"\n({detail})" if detail else "")
            self._status_label.configure(text="")
            showerror("Erro", hint)

    def _finish_and_go_home(self) -> None:
        if not self._copied_ready or self._busy.is_set():
            return
        self._on_ready_for_flow()
