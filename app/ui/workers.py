"""Qt workers (QThread) to keep the GUI responsive."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.models.models import OverlaySettings, QueueItem, VideoSettings, YouTubeMetadata
from app.templates import parse_tags
from app.utils.files import ensure_dir, safe_stem


class FFmpegWorker(QThread):
    progress = Signal(float, float, float)  # out_s, total, pct
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, ffmpeg_service, image: str, audio: str, output: str,
                 vs: VideoSettings, ov: OverlaySettings, parent=None) -> None:
        super().__init__(parent)
        self._svc = ffmpeg_service
        self._image = image
        self._audio = audio
        self._output = output
        self._vs = vs
        self._ov = ov
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            def _cb(out_s: float, total: float, pct: float):
                self.progress.emit(out_s, total, pct)

            path = self._svc.generate(
                self._audio, self._image, self._output, self._vs, self._ov,
                on_progress=_cb, cancel_event=self.cancel_event)
            self.finished_ok.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc) or repr(exc))

    def cancel(self) -> None:
        self.cancel_event.set()
        try:
            self._svc.cancel()
        except Exception:
            pass


class UploadWorker(QThread):
    progress = Signal(int, int, float)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, yt_service, video_path: str, meta: YouTubeMetadata,
                 channel_id: str = "", playlist_id: str = "", parent=None) -> None:
        super().__init__(parent)
        self._svc = yt_service
        self._video = video_path
        self._meta = meta
        self._channel = channel_id
        self._playlist = playlist_id
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            def _cb(sent: int, total: int, pct: float):
                self.progress.emit(sent, total, pct)

            result = self._svc.upload_video(
                self._video, self._meta, channel_id=self._channel,
                playlist_id=self._playlist, on_progress=_cb,
                cancel_event=self.cancel_event)
            self.finished_ok.emit(dict(result))
        except Exception as exc:
            msg = getattr(exc, "user_message", None) or str(exc) or repr(exc)
            self.failed.emit(msg)

    def cancel(self) -> None:
        self.cancel_event.set()


class ChannelWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, yt_service, parent=None) -> None:
        super().__init__(parent)
        self._svc = yt_service

    def run(self) -> None:
        try:
            channels = self._svc.list_channels()
            self.finished_ok.emit(list(channels))
        except Exception as exc:
            msg = getattr(exc, "user_message", None) or str(exc) or repr(exc)
            self.failed.emit(msg)


class OAuthWorker(QThread):
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, auth, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth

    def run(self) -> None:
        try:
            self._auth.run_consent_flow()
            self.finished_ok.emit()
        except Exception as exc:
            msg = getattr(exc, "user_message", None) or str(exc) or repr(exc)
            self.failed.emit(msg)


def vars_for(item: QueueItem) -> dict:
    return {
        "id": item.id, "beat_name": item.beat_name, "audio_path": item.audio_path,
        "artwork_path": item.artwork_path, "title": item.title,
        "description": item.description, "tags": item.tags,
        "category_id": item.category_id, "privacy": item.privacy,
        "channel_id": item.channel_id, "video_path": item.video_path,
        "publish_at": item.publish_at,
    }


class _BatchBase(QThread):
    """Base class for batch workers: iterate items with progress and cancel."""

    item_started = Signal(int)
    item_progress = Signal(int, float)
    item_failed = Signal(int, str)
    all_done = Signal()

    def __init__(self, svc, items: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.svc = svc
        self.items = items
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True
        try:
            self.svc.cancel()
        except Exception:
            pass

    def _prepare(self) -> None:
        """Pre-batch hook (e.g. create the output directory)."""

    def _run_item(self, item: dict, progress_cb) -> object:
        """Process one item. Return the payload for item_done."""
        raise NotImplementedError

    def _succeed(self, item_id: int, payload: object) -> None:
        raise NotImplementedError

    @staticmethod
    def _fail_message(exc: Exception) -> str:
        return getattr(exc, "user_message", None) or str(exc) or repr(exc)

    def run(self) -> None:
        self._prepare()
        for it in self.items:
            if self._cancel:
                break
            iid = int(it["id"])
            self.item_started.emit(iid)
            try:
                def _cb(o, t, pct, _iid=iid):
                    self.item_progress.emit(_iid, pct)
                payload = self._run_item(it, _cb)
                self._succeed(iid, payload)
            except Exception as exc:
                self.item_failed.emit(iid, self._fail_message(exc))
        self.all_done.emit()


class BatchGenerateWorker(_BatchBase):
    item_done = Signal(int, str)

    def __init__(self, video_gen, items: list[dict], vs: VideoSettings,
                 ov: OverlaySettings, out_dir: str, parent=None) -> None:
        super().__init__(video_gen, items, parent)
        self.vs = vs
        self.ov = ov
        self.out_dir = out_dir

    def _prepare(self) -> None:
        ensure_dir(self.out_dir)

    def _run_item(self, item: dict, progress_cb) -> object:
        out = Path(self.out_dir) / f"{safe_stem(item.get('beat_name') or Path(item['audio_path']).stem)}.mp4"
        self.svc.generate(item["audio_path"], item["artwork_path"], out,
                          self.vs, self.ov, on_progress=progress_cb)
        return str(out)

    def _succeed(self, item_id: int, payload: object) -> None:
        self.item_done.emit(item_id, str(payload))


class BatchUploadWorker(_BatchBase):
    item_done = Signal(int, dict)

    def cancel(self) -> None:
        self._cancel = True

    def _run_item(self, item: dict, progress_cb) -> object:
        meta = YouTubeMetadata(
            title=item.get("title", ""), description=item.get("description", ""),
            tags=parse_tags(item.get("tags", "")),
            category_id=item.get("category_id", "10") or "10",
            privacy=item.get("privacy", "private"),  # type: ignore[arg-type]
            publish_at=item.get("publish_at", "") or "",
        )
        res = self.svc.upload_video(item["video_path"], meta,
                                    channel_id=item.get("channel_id", ""),
                                    on_progress=progress_cb)
        return dict(res)

    def _succeed(self, item_id: int, payload: object) -> None:
        assert isinstance(payload, dict)
        self.item_done.emit(item_id, payload)
