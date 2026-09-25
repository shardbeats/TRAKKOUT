"""Template loading/applying/editing (mixin)."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QDialog, QMessageBox

from app.templates import DEFAULT_PRESETS, create_default_presets

log = logging.getLogger(__name__)



class TemplatesMixin:
    def _reload_templates(self, select: str = ""):
        self.cb_template.clear()

        # Create default presets if missing
        if not hasattr(self, '_presets_loaded'):
            create_default_presets()
            self._presets_loaded = True

        # List all available presets
        preset_names = self.presets.list_presets()

        seen = set()
        for name in preset_names:
            try:
                t = self.presets.get_preset(name)
                display_name = t.get("name", name)
                if display_name in seen:
                    continue
                seen.add(display_name)
                self.cb_template.addItem(display_name, t)
                log.info(f"[Templates] Loaded preset: {display_name}")
            except FileNotFoundError as e:
                log.warning(f"[Templates] Preset not found: {name} - {e}")
                continue

        # If no presets loaded, fall back to built-ins
        if not preset_names:
            for key, data in DEFAULT_PRESETS.items():
                display_name = data["name"]
                self.cb_template.addItem(display_name, data)
                log.info(f"[Templates] Loaded default preset: {display_name}")

        if select:
            idx = self.cb_template.findText(select)
            if idx >= 0:
                self.cb_template.setCurrentIndex(idx)

    def _apply_template(self):
        t = self.cb_template.currentData()
        if not t:
            return

        vals = self._template_vals()

        # Render title, description and tags
        title = self.engine.render(t.get("title", ""), vals)
        desc = self.engine.render(t.get("description", ""), vals)
        tags = self.engine.render(t.get("tags", ""), vals)

        self.ed_title.setText(title)
        self.ed_desc.setPlainText(desc)
        self.ed_tags.setText(tags)

        # Apply category if the preset has one
        if t.get("category"):
            idx = self.cb_cat.findData(str(t["category"]))
            if idx >= 0:
                self.cb_cat.setCurrentIndex(idx)

        # Apply privacy if configured
        if t.get("privacy") in ("private", "unlisted", "public"):
            if not self.ck_schedule.isChecked():
                self.cb_privacy.setCurrentText(t["privacy"])

        # Check for missing variables
        missing = self.engine.missing_variables(title + "\n" + desc + "\n" + tags, vals)
        if missing:
            self._set_status(f"Template applied: {t.get('name')} "
                             f"(missing value for: {', '.join(missing)})")
        else:
            self._set_status(f"Template applied: {t.get('name')}")

        log.info(f"[Templates] Applied template: {t.get('name')}")

    def _on_tpl_new(self):
        from app.ui.template_editor import TemplateEditorDialog
        dlg = TemplateEditorDialog(self.engine, None, self._template_vals(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.result()
        if not data["name"]:
            QMessageBox.warning(self, "Template", "Name is required.")
            return
        try:
            self.presets.get_preset(data["name"])
            exists = True
        except FileNotFoundError:
            exists = False
        if exists:
            ret = QMessageBox.question(self, "Template",
                                       f"'{data['name']}' already exists. Overwrite?")
            if ret != QMessageBox.Yes:
                return
        self.presets.save_preset(data["name"], data["title"], data["description"], data["tags"])
        self._reload_templates(select=data["name"])
        self._set_status(f"Template saved: {data['name']}")

    def _on_tpl_edit(self):
        from app.ui.template_editor import TemplateEditorDialog
        t = self.cb_template.currentData()
        if not t:
            QMessageBox.information(self, "Template", "No template selected.")
            return
        dlg = TemplateEditorDialog(self.engine, dict(t), self._template_vals(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.result()
        self.presets.save_preset(data["name"], data["title"], data["description"], data["tags"])
        self._reload_templates(select=data["name"])
        self._set_status(f"Template updated: {data['name']}")

    def _on_tpl_delete(self):
        t = self.cb_template.currentData()
        if not t:
            return
        name = t.get("name", "")
        extra = " (it will be restored on restart)" if name == "Free Standard" else ""
        ret = QMessageBox.question(self, "Template",
                                   f"Delete '{name}'?{extra}")
        if ret != QMessageBox.Yes:
            return
        if not self.presets.delete_preset(name):
            QMessageBox.warning(self, "Template", f"Could not delete '{name}'.")
            return
        # Prune the ghost copy in settings so it does not come back.
        try:
            self.settings.templates = [x for x in (self.settings.templates or [])
                                       if x.get("name") != name]
            self.store.save()
        except Exception as exc:
            log.warning("Could not update settings after delete: %s", exc)
        self._reload_templates()
        self._set_status(f"Template deleted: {name}")

    def _persist_ui_to_settings(self):
        s = self.settings

        # Currently selected template
        t = self.cb_template.currentData()

        s.resolution = self.cb_res.currentText()
        s.fit_mode = self.cb_fit.currentText()
        s.blurred_background = self.ck_blur.isChecked()
        s.background_color = self.ed_bg.text().strip() or "000000"
        s.audio_format = self.cb_afmt.currentText()
        s.audio_bitrate = self.cb_abr.currentText()
        s.video_preset = self.cb_preset.currentText()
        s.overlay_enabled = self.ck_overlay.isChecked()
        s.overlay_text = self.ed_overlay.text()
        s.overlay_position = self.cb_ov_pos.currentText()
        s.overlay_font_size = int(self.sp_ov_size.value())
        s.overlay_opacity = float(self.sp_ov_op.value())
        s.overlay_margin = int(self.sp_ov_margin.value())
        s.default_privacy = self.cb_privacy.currentText()
        s.default_category = str(self.cb_cat.currentData() or "10")
        s.made_for_kids = self.ck_kids.isChecked()

        # Store selected template in settings
        if t:
            s.templates = [t]

        try:
            self.store.save()
        except Exception as exc:
            log.warning("Could not save settings: %s", exc)
