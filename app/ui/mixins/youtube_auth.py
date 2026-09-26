"""OAuth, channels and account status (mixin)."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

from app.models.models import ChannelInfo
from app.ui.workers import ChannelWorker, OAuthWorker

log = logging.getLogger(__name__)



class YouTubeAuthMixin:
    def _startup_checks(self):
        st = self.ffmpeg.status()
        if not st.ffmpeg_ok or not st.ffprobe_ok:
            QMessageBox.warning(
                self, "FFmpeg not found",
                "FFmpeg/FFprobe were not found on the PATH.\n\n"
                f"FFmpeg: {st.ffmpeg}\nFFprobe: {st.ffprobe}\n\n"
                "Install FFmpeg (winget install Gyan.FFmpeg) or set the path in File > Settings.\n"
                "Video generation will not work until then.")
            self._set_status("FFmpeg unavailable. Check Settings.")
        else:
            self._set_status(f"Ready. {st.ffmpeg_version}")

        ok, msg = self.auth.validate_client_secrets()
        if not ok:
            self.txt_log.appendPlainText("[OAuth] " + msg)

        # If connected, refresh channels (may fail on expired tokens)
        if self.yt.is_connected():
            try:
                self._on_refresh_channels(silent=True)
            except Exception as exc:
                log.warning(f"[YouTube] Error refreshing channels: {exc}")
                # On expired tokens, show a message and allow reconnecting
                if self._is_token_expired(exc):
                    self._show_token_expired()

        self._update_yt_status()

    # ================= helpers =================

    def _update_yt_status(self):
        connected = self.yt.is_connected()
        self.lbl_yt_status.setText("Connected" if connected else "Disconnected")
        try:
            self.lbl_yt_status.setStyleSheet("color:green;" if connected else "color:#aa5500;")
        except Exception as exc:
            log.warning(f"[YouTube] Error updating status: {exc}")
        # Sidebar footer with the real status (nothing hardcoded).
        try:
            name = ""
            if connected:
                ch = self._selected_channel()
                if ch is None and self.channels:
                    ch = self.channels[0]
                name = ch.title if ch and ch.title else "Connected"
            self.sidebar.set_account(connected, name if connected else "Not connected")
        except Exception as exc:
            log.warning(f"[YouTube] Error updating sidebar: {exc}")

    def _on_connect(self):
        ok, msg = self.auth.validate_client_secrets()
        if not ok:
            QMessageBox.warning(self, "Google OAuth", msg)
            self._show_oauth_help()
            return
        self._set_status("Opening browser to authorize with Google…")
        self._oauth_worker = OAuthWorker(self.auth, self)
        self._oauth_worker.finished_ok.connect(self._on_oauth_ok)
        self._oauth_worker.failed.connect(self._on_oauth_fail)
        self._oauth_worker.start()

    def _on_oauth_ok(self):
        self._set_status("Google account connected.")
        self._update_yt_status()
        self._on_refresh_channels()

    def _on_oauth_fail(self, msg: str):
        # Friendlier message on expired tokens
        if self._is_token_expired(msg):
            self._show_token_expired(msg)
        else:
            QMessageBox.warning(self, "Google OAuth", f"Could not connect.\n{msg}")

        self._set_status("OAuth cancelled or failed.")

    def _on_disconnect(self):
        ret = QMessageBox.question(self, "Disconnect", "Delete this computer's Google token?")
        if ret != QMessageBox.Yes:
            return
        self.auth.disconnect()
        self.channels = []
        self.cb_channel.clear()
        self._update_yt_status()
        self._set_status("Google session removed.")

    def _on_refresh_channels(self, silent: bool = False):
        if not self.yt.is_connected():
            if not silent:
                QMessageBox.information(self, "Channels", "Connect your Google account first.")
            return

        try:
            self._set_status("Fetching channels...")
            self._ch_worker = ChannelWorker(self.yt, self)
            self._ch_worker.finished_ok.connect(self._on_channels_ok)
            self._ch_worker.failed.connect(lambda m: self._on_channels_fail(m, silent))
            self._ch_worker.start()
        except Exception as exc:
            log.warning(f"[YouTube] Error refreshing channels: {exc}")
            if not silent and self._is_token_expired(exc):
                self._show_token_expired()

    def _on_channels_ok(self, channels: list):
        self.channels = list(channels)
        self.cb_channel.blockSignals(True)
        self.cb_channel.clear()
        for ch in self.channels:
            assert isinstance(ch, ChannelInfo)
            self.cb_channel.addItem(f"{ch.title}  [{ch.channel_id}]", ch.channel_id)
        self.cb_channel.blockSignals(False)

        # Restore last channel if still available
        last = self.settings.last_channel_id
        if last:
            for i in range(self.cb_channel.count()):
                if self.cb_channel.itemData(i) == last:
                    self.cb_channel.setCurrentIndex(i)
                    break

        self._update_yt_status()

        # Warn when there are no channels
        if not self.channels:
            QMessageBox.warning(self, "Channels",
                                "This account has no YouTube channel. Create one at youtube.com first.")
        else:
            self._set_status(f"{len(self.channels)} channel(s) available. "
                             "For more Brand Accounts, switch channels by re-authenticating.")

        self.txt_log.appendPlainText(f"[YouTube] channels: {[c.display for c in self.channels]}")

    def _on_channels_fail(self, msg: str, silent: bool = False):
        self._set_status("Could not fetch channels.")

        # Friendlier message on expired tokens
        if not silent and self._is_token_expired(msg):
            self._show_token_expired(msg)
        elif not silent:
            QMessageBox.warning(self, "Channels", f"Could not fetch channels.\n{msg}")

    def _on_channel_changed(self, idx: int):
        if idx < 0:
            return
        cid = self.cb_channel.itemData(idx) or ""
        self.settings.last_channel_id = str(cid)
        try:
            self.store.save()
        except Exception as exc:
            log.warning(f"[Settings] Error saving channel: {exc}")

    def _selected_channel(self) -> ChannelInfo | None:
        idx = self.cb_channel.currentIndex()
        if idx < 0 or not self.channels:
            return None
        cid = self.cb_channel.itemData(idx)
        for ch in self.channels:
            if ch.channel_id == cid:
                return ch
        return None

    def _show_oauth_help(self):
        QMessageBox.information(
            self, "Set up Google OAuth",
            "1) Go to Google Cloud Console (console.cloud.google.com) and create a project.\n"
            "2) APIs & Services > Library > enable 'YouTube Data API v3'.\n"
            "3) APIs & Services > OAuth consent screen > External > fill in app + scopes "
            "'youtube.upload' and 'youtube' > add your email as a Test user.\n"
            "4) Credentials > Create Credentials > OAuth client ID > Desktop app > Download JSON.\n"
            f"5) Save that downloaded file in:\n{self.auth.client_secrets_path.parent}\n"
            "(any client_secret*.json name works, no need to rename).\n\n"
            "6) Come back here and press 'Connect Google Account'.\n"
            "See README section 5 for the full walkthrough.")
