"""Nueva sesión de beat: reset total del formulario (mixin).

Regla: el audio define la sesión. Elegir un audio distinto al de la
sesión actual (o pulsar Clear) ⇒ flush+unlink del historial y limpieza
de todos los metadatos a defaults. El registro nuevo se crea solo al
generar/subir/fallar (vía _log_history); las filas viejas nunca se tocan.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.models import BeatMetadata

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol as _MixinBase
else:
    _MixinBase = object

log = logging.getLogger(__name__)


class SessionMixin(_MixinBase):  # type: ignore[misc]
    # ================= orchestration =================

    def _begin_audio_session(self, path: str) -> bool:
        """Prepara la sesión para `path`. Devuelve True si hubo reset."""
        prev = getattr(self, "_session_audio", "") or ""
        if path and path != prev:
            keep_cover = ""
            if getattr(self, "_fresh_cover", False):
                # Cover elegido justo antes (flujo cover-primero): es del
                # beat nuevo, no se borra. One-shot, se consume aquí.
                keep_cover = self.ed_cover.text().strip()
            # Lo pendiente pertenece a la entrada vieja: se conserva.
            self._flush_history_link()
            self._set_history_link(None)
            self._reset_form_to_defaults(
                preserve_cover=keep_cover or None)
            self._session_audio = path
            self._set_status("New audio loaded — form reset for a new record.")
            log.info("New beat session: %s", path)
            return True
        return False

    # ================= full reset =================

    def _reset_form_to_defaults(self, preserve_cover: str | None = None) -> None:
        """Limpia metadatos a defaults. No toca historial ni prefs de video.

        No llama a _refresh_media_info/_update_trim_range: el llamador
        (probe tras pick, o _clear_media) se encarga del refresco.
        """
        s = self.settings
        self.beat = BeatMetadata()
        self.audio_info = None
        self.image_info = None

        self.ed_audio.clear()
        if preserve_cover:
            self.ed_cover.setText(preserve_cover)
        else:
            self.ed_cover.clear()
        for w in (self.ed_beat, self.ed_artist, self.ed_artist2,
                  self.ed_producer, self.ed_genre, self.ed_bpm,
                  self.ed_key, self.ed_purchase, self.ed_title,
                  self.ed_tags, self.ed_playlist):
            w.clear()
        self.ed_desc.setPlainText("")

        idx = self.cb_cat.findData(s.default_category or "10")
        self.cb_cat.setCurrentIndex(idx if idx >= 0 else 0)
        priv = s.default_privacy if s.default_privacy in (
            "private", "unlisted", "public") else "private"
        self.cb_privacy.setCurrentText(priv)
        self.cb_privacy.setEnabled(True)
        self.ck_kids.setChecked(bool(s.made_for_kids))
        self.ck_schedule.setChecked(False)

        self.ck_overlay.setChecked(bool(s.overlay_enabled))
        self.ed_overlay.setText(s.overlay_text or "")
        self.cb_ov_pos.setCurrentText(s.overlay_position or "bottom-center")
        try:
            self.sp_ov_size.setValue(int(s.overlay_font_size or 48))
            self.sp_ov_op.setValue(float(s.overlay_opacity or 0.9))
            self.sp_ov_margin.setValue(int(s.overlay_margin or 60))
        except Exception:
            pass

        self.sp_trim_start.setValue(0.0)
        self.sp_trim_end.setValue(0.0)
        try:
            self.wave.clear()
        except Exception:
            pass
        try:
            self.lbl_cover_prev.clear()
        except Exception:
            pass
        self._trim_audio_path = ""
        self._wave_audio_path = ""
        self.current_video = ""
        self._last_trim = (0.0, 0.0)
        self._last_gen_audio = ""
        self._op_start = 0.0
        self._op_total = 0.0
