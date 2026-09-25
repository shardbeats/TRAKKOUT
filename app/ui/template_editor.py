"""Template editor: create/edit presets with live preview."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.templates import TemplateEngine


class TemplateEditorDialog(QDialog):
    """Edit a preset {name, title, description, tags}.

    - preset None → new template (editable name).
    - preview renders with `values` (current beat context).
    - result() returns the dict ready for PresetManager.save_preset().
    """

    def __init__(self, engine: TemplateEngine, preset: dict | None = None,
                 values: dict | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._base = dict(preset or {})
        self._values = values or {}
        self._is_new = preset is None
        self.setWindowTitle("New template" if self._is_new else f"Edit: {self._base.get('name', '')}")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        lay.addLayout(form)

        self.ed_name = QLineEdit(self._base.get("name", ""))
        self.ed_name.setPlaceholderText("Preset name")
        self.ed_name.setReadOnly(not self._is_new)
        form.addRow("Name:", self.ed_name)

        # Variable combo + per-field insert buttons.
        var_row = QHBoxLayout()
        self.cb_var = QComboBox()
        self.cb_var.addItems([f"{{{{{n}}}}}" for n in engine.variable_names()])
        var_row.addWidget(QLabel("Variable:"))
        var_row.addWidget(self.cb_var, 1)
        lay.addLayout(var_row)

        self.ed_title = QLineEdit(self._base.get("title", ""))
        self.ed_tags = QLineEdit(self._base.get("tags", ""))
        self.ed_desc = QTextEdit()
        self.ed_desc.setPlainText(self._base.get("description", ""))
        self.ed_desc.setFixedHeight(110)
        form.addRow("Title:", self._row(self.ed_title))
        form.addRow("Description:", self._row(self.ed_desc))
        form.addRow("Tags:", self._row(self.ed_tags))

        for widget in (self.ed_title, self.ed_tags):
            widget.textChanged.connect(self._update_preview)
        self.ed_desc.textChanged.connect(self._update_preview)

        gb = QGroupBox("Live preview")
        gl = QVBoxLayout(gb)
        self.lbl_prev_title = QLabel()
        self.lbl_prev_title.setWordWrap(True)
        self.lbl_prev_desc = QLabel()
        self.lbl_prev_desc.setWordWrap(True)
        self.lbl_prev_tags = QLabel()
        self.lbl_prev_tags.setWordWrap(True)
        self.lbl_prev_missing = QLabel()
        self.lbl_prev_missing.setWordWrap(True)
        for w in (self.lbl_prev_title, self.lbl_prev_desc, self.lbl_prev_tags, self.lbl_prev_missing):
            gl.addWidget(w)
        lay.addWidget(gb)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)
        self._update_preview()

    def _row(self, field) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(field, 1)
        ins = QPushButton("+")
        ins.setToolTip("Insert the selected variable here")
        ins.setFixedWidth(32)
        ins.clicked.connect(lambda checked=False, f=field: self._insert_var(f))
        h.addWidget(ins)
        return w

    def _insert_var(self, field) -> None:
        var = self.cb_var.currentText()
        if isinstance(field, QLineEdit):
            field.insert(var)
        else:
            field.textCursor().insertText(var)
        field.setFocus()

    def _texts(self) -> tuple[str, str, str]:
        return (self.ed_title.text(), self.ed_desc.toPlainText(), self.ed_tags.text())

    def _update_preview(self):
        title, desc, tags = self._texts()
        self.lbl_prev_title.setText(f"<b>Title:</b> {self._engine.render(title, self._values) or '—'}")
        rendered_desc = self._engine.render(desc, self._values)
        self.lbl_prev_desc.setText(f"<b>Description:</b> {(rendered_desc[:300] + '…') if len(rendered_desc) > 300 else rendered_desc or '—'}")
        self.lbl_prev_tags.setText(f"<b>Tags:</b> {self._engine.render(tags, self._values) or '—'}")
        missing = self._engine.missing_variables(title + "\n" + desc + "\n" + tags, self._values)
        self.lbl_prev_missing.setText(f"<i>Missing value for: {', '.join(missing)}</i>" if missing else "")

    def result(self) -> dict:
        """Preset ready to save (keeps extra keys like category)."""
        title, desc, tags = self._texts()
        out = dict(self._base)
        out.update({"name": self.ed_name.text().strip(), "title": title,
                    "description": desc, "tags": tags})
        return out
