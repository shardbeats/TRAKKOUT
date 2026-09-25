# Conectar TRAKKOUT con Google Cloud (guía detallada)

Guía paso a paso para crear tu propio proyecto de Google Cloud, activar la
YouTube Data API v3 y dejar la app funcionando. Cada persona usa SUS
propias claves: el proyecto no incluye ninguna (ver `MAINTENANCE.md`).

Tiempo estimado: 15–20 minutos. Coste: 0 (capa gratuita).

---

## 0. Qué vas a conseguir y cómo funciona

- La app **no sube con una cuenta compartida**: abre tu navegador, Google te
  pide permiso y guarda un token **en tu PC**:
  `%APPDATA%\TRAKKOUT\token.json`.
- Para eso necesita un `client_secrets.json` **tuyo**, que vas a crear abajo y
  colocar en `%APPDATA%\TRAKKOUT\client_secrets.json`.
- Permisos (scopes) que pide la app: `youtube.upload` y `youtube`.
- Durante el login la app escucha en `http://localhost:8765` (puerto local,
  no necesitas abrir nada en el router; si otro programa usa ese puerto,
  ciérralo antes).
- El token se **refresca solo**. Si caduca del todo, la app te avisa y
  reconectas con un clic.

## 1. Crear el proyecto

1. Entra en [console.cloud.google.com](https://console.cloud.google.com/)
   con tu cuenta de Google.
2. Arriba a la izquierda, desplegable de proyecto → **New Project**.
3. Nombre: `trakkout` (o el que quieras) → **Create**. Espera a que se
   seleccione (la notificación tarda ~30 s).

## 2. Activar YouTube Data API v3

1. Menú ☰ → **APIs & Services → Library**.
2. Busca **YouTube Data API v3** → **Enable**.
3. Sin este paso verás el error claro: *"YouTube Data API v3 is not
   enabled…"*.

## 3. Pantalla de consentimiento OAuth (obligatorio)

1. Menú ☰ → **Google Auth platform → Branding** (antes: *OAuth consent screen*).
2. **User type: External** → Create.
3. Rellena lo mínimo:
   - App name: `TRAKKOUT`
   - User support email: tu correo
   - Developer contact: tu correo
4. **Scopes:** pulsa *Add or remove scopes* y añade:
   - `.../auth/youtube.upload`
   - `.../auth/youtube`
5. **Test users (MUY IMPORTANTE):** añade tu cuenta de Gmail con *Add users*.
   Mientras la app esté en modo *Testing* (lo normal para uso personal),
   **solo esas cuentas pueden iniciar sesión**. Si olvidas este paso, Google
   responde `access_denied` (error 403).
6. Guarda. No necesitas verificar la app ni publicar nada: para uso personal
   el modo Testing es suficiente.

## 4. Crear el cliente OAuth (Desktop)

1. Menú ☰ → **Google Auth platform → Clients** (antes: *APIs & Services →
   Credentials*).
2. **Create Client** → Application type: **Desktop app** (¡no Web!).
3. Nombre: `TRAKKOUT Desktop` → **Create**.
4. **Download JSON** (botón de descarga del cliente recién creado).

## 5. Colocar el JSON donde la app lo espera

1. En Windows, abre `%APPDATA%\TRAKKOUT\` (pégalo en la barra del
   Explorador). Si no existe, crea la carpeta o abre la app una vez.
2. Copia el JSON descargado ahí con el nombre exacto:
   **`client_secrets.json`** (minúsculas, sin `-copia`, sin `(1)`).
3. Comprueba que empieza por `{"installed": ...` (Desktop) y no por `{"web"`.

## 6. Conectar desde la app

1. Abre TRAKKOUT → YouTube → **Connect Google Account**.
2. Se abre el navegador: elige tu cuenta (la misma de Test users) →
   **Advanced/Continuar** si aparece el aviso *"Google hasn't verified this
   app"* (normal: es TU app en Testing, pulsa *Go to TRAKKOUT*) →
   marca los dos permisos → **Continue**.
3. El navegador muestra *"The authentication flow has completed"* y puedes
   cerrarlo. La app pasa a **Connected** y lista tus canales (**Refresh
   Channels** si hace falta).
4. Si tienes varios canales/Brand Accounts: la API publica **siempre** en el
   canal de la sesión activa. Para cambiar de canal: **Disconnect** en la app
   y reconecta eligiendo ESE canal en el selector de cuentas de Google.

## 7. Cuota (cuánto puedes subir)

- Los proyectos nuevos traen **10.000 unidades/día**. Cada subida
  (`videos.insert`) cuesta **~1.600** → unas **6 subidas al día**, de sobra
  para uso personal. Los listados de canales casi no consumen.
- Si ves *"quota exhausted"*: espera al día siguiente (resetea a medianoche
  hora del Pacífico) o pide ampliación en Cloud Console → *Quotas*.
- La cuota es **por proyecto = por persona**: tu uso no afecta al de nadie.

## 8. Problemas típicos (mensaje → causa → solución)

| Lo que ves | Causa | Solución |
|---|---|---|
| `client_secrets.json not found` | Mal nombre/ruta | Debe ser `%APPDATA%\TRAKKOUT\client_secrets.json` exacto |
| `not valid JSON` / sin sección `installed` | JSON equivocado | Descarga de nuevo el cliente **Desktop app** (paso 4) |
| `access_denied` / Error 403 al loguearte | Tu email no está en Test users | Paso 3.5: añádelo y reintenta |
| *"Google hasn't verified this app"* | Normal en Testing | Advanced → Go to TRAKKOUT → Continue |
| `YouTube Data API v3 is not enabled` | Falta el paso 2 | Library → Enable |
| `redirect_uri_mismatch` | Cliente tipo Web en vez de Desktop | Crea un cliente **Desktop app** nuevo |
| `invalid_grant` / sesión expirada | Token revocado o caducado | Pulsa Connect de nuevo (borra `token.json` si persiste) |
| `quota exhausted` | Cuota diaria agotada | Espera al día siguiente |
| El navegador no se abre | Puerto 8765 ocupado o sin navegador | Cierra lo que use el 8765; copia la URL a tu navegador |
| Publica en el canal equivocado | Sesión activa ≠ canal elegido | Disconnect + reconecta eligiendo ese canal |

## 9. Seguridad (léelo una vez)

- `client_secrets.json` y `token.json` son **tus llaves**: no los subas a
  GitHub, no los pases por chat, no los metas en el repo (el `.gitignore` ya
  los excluye).
- Puedes revocar el acceso cuando quieras en
  https://myaccount.google.com/permissions (busca *TRAKKOUT*) y borrar
  `%APPDATA%\TRAKKOUT\token.json` para desconectar del todo.
- Los tokens en `logs/app.log` se redactan automáticamente.

## 10. Referencias oficiales

- OAuth Desktop Apps: https://developers.google.com/youtube/v3/guides/auth/installed-apps
- Crear credenciales: https://developers.google.com/workspace/guides/create-credentials
- Clientes OAuth: https://console.cloud.google.com/auth/clients
- Cuotas: Cloud Console → APIs & Services → Quotas
