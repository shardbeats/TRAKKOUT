"""Compat: QueueHistoryMixin = QueueMixin + HistoryMixin (Fase 3).

Se mantiene para no romper imports existentes (`MainWindow`,
tests). El código vive en queue_mixin.py e history_mixin.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.mixins.history_mixin import HistoryMixin, paint_history_row
from app.ui.mixins.queue_mixin import QueueMixin

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol as _MixinBase
else:
    _MixinBase = object


class QueueHistoryMixin(QueueMixin, HistoryMixin, _MixinBase):  # type: ignore[misc]
    """Shim de compatibilidad. Hereda todo de Queue + History."""


__all__ = ["QueueHistoryMixin", "QueueMixin", "HistoryMixin", "paint_history_row"]
