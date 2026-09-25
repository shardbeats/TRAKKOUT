# Guía de mantenimiento — TRAKKOUT

Guía práctica para mantener esta aplicación funcionando durante años.
Idioma del documento: español (el código y la UI están en inglés).

## 1. Mapa del proyecto (qué toca qué)

```
trakkout/
├── app/main.py              Entrada. Crea QApplication, aplica tema, abre MainWindow.
├── app/ui/main_window.py    Cascarón: __init__ + _build_ui + closeEvent (~460 líneas).
├── app/ui/mixins/           TODA la lógica de la ventana, por dominio:
│   ├── base.py              Estado, progreso, navegación, historial, ajustes.
│   ├── collectors.py        Lectura widgets → modelos (video/audio/overlay/beat).
│   ├── media.py             Audio/portada, drag&drop, probe, autodetección BPM/key.
│   ├── templates_ui.py      Cargar/aplicar/crear/editar/borrar plantillas.
│   ├── youtube_auth.py      OAuth, canales, estado de cuenta.
│   ├── generate_upload.py   Generar vídeo, preview, subir, cancelar.
│   └── queue_history.py     Cola por lotes e historial SQLite.
├── app/ui/workers.py        Hilos Qt (FFmpeg, Upload, OAuth, Channels, Batch).
├── app/ui/dialogs.py        Diálogos Ajustes y Preview.
├── app/ui/template_editor.py Editor de plantillas con preview en vivo.
├── app/ui/sections.py       Sidebar + secciones plegables (solo UI).
├── app/ui/theme.py + style.qss  Tema oscuro (se edita sin tocar código).
├── app/templates/           Motor {{variable}} (engine.py), presets JSON (presets.py),
│                            tags.py, compatibilidad {var} (compat.py).
├── app/services/
│   ├── video_generator.py    Generación de vídeo con FFmpeg.
│   ├── queue_manager.py      Cola persistente en SQLite (tabla `queue`;
│   │                         al arrancar normaliza Generating/Uploading→Pending,
│   │                         descarta Uploaded/Scheduled y revalida Ready).
│   └── history_store.py      Historial SQLite (tabla `history`; automigra las
│                             columnas title/description/tags/category_id).
├── app/models/models.py      Modelos (BeatMetadata con artist2, HistoryEntry con
│                             metadata para Load, VideoSettings.is_vertical).
├── app/ffmpeg/              Todo lo que habla con ffmpeg/ffprobe.
├── app/youtube/             OAuth (auth.py), errores HTTP (errors.py), subidas (youtube_service.py).
├── app/config/settings.py   settings.json en %APPDATA%\TRAKKOUT.
├── app/utils/beat_names.py  Parser título/BPM/key desde el nombre del archivo.
├── app/resources/templates/ Presets (Free Standard.json). Se recrean solos si faltan.
├── build_exe.py + TRAKKOUT.spec  Receta del portable (PyInstaller, one-file).
└── requirements.txt         Dependencias congeladas por rango (>=).
```

**Regla de oro:** la UI (`app/ui`) nunca habla con Google ni con FFmpeg
directamente; siempre a través de `VideoGenerator`, `YouTubeService` y
`PresetManager`. Si respetas eso, los cambios no se rompen entre sí.

## 2. Calendario de mantenimiento sugerido

| Cuándo | Tarea | Dónde mirar |
|---|---|---|
| Cada 6–12 meses | Actualizar dependencias (`pip install -U ...`, ver §3) | `requirements.txt`, `pyproject.toml` |
| Cada 12 meses | Probar el flujo OAuth completo (conectar → canales → subir en privado) | Google Cloud Console + app |
| Cada 12 meses | Revisar avisos de deprecación de YouTube Data API v3 | https://developers.google.com/youtube/v3/revision_history |
| Cada 12 meses | Probar con el FFmpeg estable más reciente | https://www.gyan.dev/ffmpeg/builds/ |
| Tras cada cambio | Regenerar el exe y probarlo en una carpeta limpia | `build_exe.py` |
| Siempre | Nunca commitear `client_secrets.json`, `token.json`, `*.db`, `*.log` | `.gitignore` ya los cubre |

## 3. Actualizar dependencias sin romper nada

1. Activa el venv y anota lo instalado: `venv\Scripts\python.exe -m pip freeze > antes.txt`
2. Actualiza por grupos (nunca todo a la vez): primero `PySide6`, luego `google-*`, luego el resto.
3. Tras cada grupo, ejecuta la app y prueba: abrir, cargar audio+portada,
   aplicar plantilla, generar 1 vídeo, conectar Google, listar canales.
4. Si algo falla: `venv\Scripts\python.exe -m pip install -r requirements.txt`
   para volver atrás, y fija el tope en el rango (p. ej. `PySide6>=6.6,<7`).
5. Solo entonces actualiza los rangos en `requirements.txt`.

**Puntos históricamente sensibles:**
- **PySide6 6.x → 7.x (cuando salga):** revisar `QDateTime`, `QFileDialog` y
  los `Signal` de `workers.py`. Probar el arranque en offscreen con la
  ventana real:
  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  venv\Scripts\python.exe -c "from PySide6.QtWidgets import QApplication; from app.config.settings import SettingsStore; from app.ui.main_window import MainWindow; from pathlib import Path; app=QApplication([]); w=MainWindow(Path('.'),SettingsStore()); print('UI OK', w.windowTitle()); w.close()"
  ```
- **google-api-python-client:** si cambia el discovery local, la subida puede
  pedir red la primera vez. El exe ya incluye `youtube.v3.json`.
- **Python:** el proyecto pide `>=3.11`. Antes de subir de versión menor
  (3.12 → 3.13…), recompila el exe: PyInstaller es sensible a la versión.

## 4. YouTube / Google Cloud (lo que más se rompe con los años)

- **Pantalla de consentimiento en Testing:** caduca el acceso si la app no se
  usa; basta reconectar. Si Google cambia los requisitos de verificación,
  cada usuario lo resuelve en SU proyecto (el repo no lleva claves).
- **Cuotas:** el proyecto usa la cuota de cada usuario, no la tuya. Si un día
  la cuota por defecto no alcanza, se amplía en Cloud Console del usuario.
- **`verify_channel_selection`:** si Google cambia el comportamiento de
  `channels.list(mine=true)` con Brand Accounts, este es el primer sitio a
  revisar (`app/youtube/youtube_service.py`).
- **Scopes:** si añades funciones (p. ej. leer comentarios), hay que añadir el
  scope en `auth.py:SCOPES` Y re-autorizar (borrar `token.json`).

## 5. FFmpeg (lo segundo que más se rompe)

- Todo el acoplamiento está en `app/ffmpeg/ffmpeg_service.py`. Si un filtro
  cambia de sintaxis en el futuro, solo se toca `build_video_filter()`.
- El recorte cuadrado usa `crop='min(iw,ih)':'min(iw,ih)'`, sintaxis estable
  desde hace años; vigilar `gblur` y `drawtext` (la fuente se autodetecta en
  `find_system_font()`).
- La app exige FFmpeg en el PATH y avisa si falta: no empaquetarlo en el exe
  es una decisión consciente (licencia + tamaño).

## 6. Recompilar el portable

```powershell
venv\Scripts\python.exe build_exe.py        # compila dist\TRAKKOUT.exe
venv\Scripts\python.exe build_exe.py --check  # solo verifica requisitos
```

- Tarda varios minutos. El aviso `No module named 'grpc'` durante el build
  es inofensivo (submódulo que la app no usa).
- Verificación rápida: arrancar el exe con `QT_QPA_PLATFORM=offscreen`,
  debe seguir vivo 20 s sin cerrarse.
- `build/` y `dist/` están ignorados por git: el exe se distribuye por
  GitHub Releases, nunca commiteado.

## 7. Checklist de release

1. `git status` limpio de secretos (`*secret*.json`, `token.json`, `*.db`, `*.log`).
2. README y GOOGLE_SETUP.md al día (rutas genéricas, dependencias = `requirements.txt`).
3. `CHANGELOG.md` con la nueva versión + bump en `pyproject.toml` y `app/__init__.py`.
4. Probar exe en carpeta/PC limpio: generar 16:9 y 9:16, cola persistente
   (cerrar y reabrir), Load/Update desde historial, subir en privado.
5. Subir el exe a GitHub Releases (el LICENSE lo genera GitHub al crear el repo).

## 8. Comportamientos decididos (no son bugs)

- **Lote usa la metadata congelada del item** (la de cuando se añadió a la
  cola); la generación individual usa el formulario en vivo. Decidido así a
  propósito: no cambiar sin repasar `_on_batch_gen_done` y `BatchUploadWorker`.
- **Historial:** se crea solo en Generate/Upload; los retoques son manuales
  con **Update from form**. No hay auto-guardado por tecla.
- **Shorts:** vertical + ≤3 min se avisa, no se bloquea; YouTube clasifica solo.
- **Tests:** hay suite en `tests/` (`python -m pytest tests -q`, CI en `.github/workflows/tests.yml`).
  Cubre lógica pura sin GUI/red/FFmpeg (utils, modelos, templates, settings, stores SQLite,
  errores de YouTube y validación OAuth). La verificación del exe sigue siendo manual
  con el checklist del punto 7.

## 9. Copias de seguridad

- Código: GitHub (remoto). Suficiente.
- Datos locales (NO están en git, y está bien): `%APPDATA%\TRAKKOUT\`
  (`settings.json`, `token.json`, `history.db`). Si cambias de PC, copia esa
  carpeta o reconfigura OAuth de cero.
- La primera versión se llamó Beat2YouTube: al arrancar, la app migra sola
  `settings.json`/`token.json`/`history.db` desde `%APPDATA%\Beat2YouTube\`
  si existe (ver `_migrate_legacy_data` en `app/config/settings.py`).
- Tus presets personalizados viven en `app\resources\templates\*.json`:
  están en git si los commiteas; si no, expórtalos antes de formatear.
