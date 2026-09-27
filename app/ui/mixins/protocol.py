"""Contrato explícito de MainWindow para los mixins (Fase 2).

Los mixins accedían a ~60 atributos de MainWindow por duck-typing.
Este Protocol documenta qué widgets, servicios, estado y métodos
debe exponer la ventana. No cambia runtime: solo sirve para
type-checkers y para saber quién es dueño de qué.

Uso:
    from app.ui.mixins.protocol import MainWindowProtocol
    class MediaMixin(MainWindowProtocol): ...
o solo como referencia en TYPE_CHECKING.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class MainWindowProtocol(Protocol):
    # ---- servicios / estado ----
    project_root: Path
    store: Any
    settings: Any
    ffmpeg: Any
    video_gen: Any
    engine: Any
    presets: Any
    auth: Any
    yt: Any
    history: Any
    queue: Any
    beat: Any
    channels: list
    current_video: str
    audio_info: Any
    image_info: Any

    # workers / operación en curso
    ffmpeg_worker: Any
    upload_worker: Any
    batch_worker: Any
    waveform_worker: Any
    _op_start: float
    _op_total: float
    _last_trim: tuple[float, float]
    _last_publish_at: str
    _trim_audio_path: str
    _wave_audio_path: str
    _last_gen_audio: str

    # history autosave
    _history_link_id: int | None
    _history_dirty: bool
    _history_save_timer: Any

    # ---- widgets (inyectados por app/ui/views/*) ----
    ed_audio: Any
    ed_cover: Any
    lbl_media_info: Any
    lbl_source: Any
    lbl_cover_prev: Any
    cb_format: Any
    cb_res: Any
    cb_fit: Any
    ck_blur: Any
    sp_fps: Any
    cb_preset: Any
    cb_afmt: Any
    cb_abr: Any
    ed_bg: Any
    wave: Any
    sp_trim_start: Any
    sp_trim_end: Any
    lbl_clip_info: Any
    ck_overlay: Any
    ed_overlay: Any
    cb_ov_pos: Any
    sp_ov_size: Any
    sp_ov_op: Any
    sp_ov_margin: Any
    lbl_yt_status: Any
    cb_channel: Any
    cb_template: Any
    ed_title: Any
    ed_desc: Any
    ed_tags: Any
    cb_cat: Any
    cb_privacy: Any
    ck_kids: Any
    ed_playlist: Any
    ed_beat: Any
    ed_artist: Any
    ed_artist2: Any
    ed_producer: Any
    ed_genre: Any
    ed_bpm: Any
    ed_key: Any
    ed_purchase: Any
    ck_schedule: Any
    dt_schedule: Any
    cb_tz: Any
    lbl_status: Any
    progress: Any
    lbl_times: Any
    tbl_queue: Any
    tbl_hist: Any
    txt_log: Any
    views: Any
    sidebar: Any
    scroll: Any
    sections_layout: Any
    _sections: dict

    # ---- métodos que los mixins pueden llamar ----
    def _set_status(self, text: str) -> None: ...
    def _set_progress(self, pct: float, label: str = "") -> None: ...
    def _set_busy(self, busy: bool) -> None: ...
    def _show_view(self, idx: int) -> None: ...
    def _refresh_queue_table(self) -> None: ...
    def _refresh_history_table(self) -> None: ...
    def _log_history(self, entry: Any) -> int | None: ...
    def _flush_history_link(self) -> None: ...
    def _set_history_link(self, entry_id: int | None) -> None: ...
    def _collect_video_settings(self) -> Any: ...
    def _collect_overlay(self) -> Any: ...
    def _collect_metadata(self) -> Any: ...
    def _collect_beat_metadata(self) -> Any: ...
    def _template_vals(self) -> dict: ...
    def _selected_channel(self) -> Any: ...
    def _persist_ui_to_settings(self) -> None: ...
    def _update_clip_visibility(self) -> None: ...
    def _update_trim_range(self) -> None: ...
    def _refresh_media_info(self) -> None: ...
