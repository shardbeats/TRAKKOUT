# Connecting TRAKKOUT to Google Cloud (detailed guide)

Step-by-step guide to create your own Google Cloud project, enable the
YouTube Data API v3 and get the app running. Everyone uses THEIR OWN
keys: the project ships none (see `MAINTENANCE.md`).

Estimated time: 15–20 minutes. Cost: 0 (free tier).

---

## 0. What you'll get and how it works

- The app does **not** upload through a shared account: it opens your browser, Google
  asks for permission, and stores a token **on your PC**:
  `%APPDATA%\TRAKKOUT\token.json`.
- For that it needs a `client_secrets.json` of **yours**, which you'll create below
  and place at `%APPDATA%\TRAKKOUT\client_secrets.json`.
- Scopes the app requests: `youtube.upload` and `youtube`.
- During login the app listens on `http://localhost:8765` (local port,
  no router changes needed; if another program uses that port,
  close it first).
- The token **refreshes itself**. If it fully expires, the app tells you and
  you reconnect with one click.

## 1. Create the project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
   with your Google account.
2. Top left, project dropdown → **New Project**.
3. Name: `trakkout` (or whatever you like) → **Create**. Wait until it
   gets selected (the notification takes ~30 s).

## 2. Enable YouTube Data API v3

1. Menu ☰ → **APIs & Services → Library**.
2. Search **YouTube Data API v3** → **Enable**.
3. Without this step you'll get the clear error: *"YouTube Data API v3 is not
   enabled…"*.

## 3. OAuth consent screen (required)

1. Menu ☰ → **Google Auth platform → Branding** (formerly *OAuth consent screen*).
2. **User type: External** → Create.
3. Fill in the minimum:
   - App name: `TRAKKOUT`
   - User support email: your email
   - Developer contact: your email
4. **Scopes:** click *Add or remove scopes* and add:
   - `.../auth/youtube.upload`
   - `.../auth/youtube`
5. **Test users (VERY IMPORTANT):** add your Gmail account with *Add users*.
   While the app is in *Testing* mode (normal for personal use),
   **only those accounts can sign in**. Skip this step and Google
   replies `access_denied` (error 403).
6. Save. No need to verify the app or publish anything: for personal use
   Testing mode is enough.

## 4. Create the OAuth client (Desktop)

1. Menu ☰ → **Google Auth platform → Clients** (formerly *APIs & Services →
   Credentials*).
2. **Create Client** → Application type: **Desktop app** (not Web!).
3. Name: `TRAKKOUT Desktop` → **Create**.
4. **Download JSON** (download button on the newly created client).

## 5. Place the JSON where the app expects it

1. On Windows, open `%APPDATA%\TRAKKOUT\` (paste it in the Explorer
   address bar). If it doesn't exist, create the folder or open the app once.
2. Copy the downloaded JSON there with the exact name:
   **`client_secrets.json`** (lowercase, no `-copy`, no `(1)`).
3. Check it starts with `{"installed": ...` (Desktop), not `{"web"`.

## 6. Connect from the app

1. Open TRAKKOUT → YouTube → **Connect Google Account**.
2. The browser opens: pick your account (the same one from Test users) →
   **Advanced/Continue** if you see the *"Google hasn't verified this
   app"* warning (normal: it's YOUR app in Testing, click *Go to TRAKKOUT*) →
   check both permissions → **Continue**.
3. The browser shows *"The authentication flow has completed"* and you can
   close it. The app switches to **Connected** and lists your channels
   (**Refresh Channels** if needed).
4. With multiple channels/Brand Accounts: the API **always** publishes to the
   active session's channel. To switch channels: **Disconnect** in the app
   and reconnect choosing THAT channel in Google's account picker.

## 7. Quota (how much you can upload)

- New projects get **10,000 units/day**. Each upload
  (`videos.insert`) costs **~1,600** → about **6 uploads a day**, plenty
  for personal use. Channel listings cost almost nothing.
- On *"quota exhausted"*: wait until next day (resets at midnight
  Pacific time) or request more in Cloud Console → *Quotas*.
- Quota is **per project = per person**: your usage doesn't affect anyone else.

## 8. Common issues (message → cause → fix)

| What you see | Cause | Fix |
|---|---|---|
| `client_secrets.json not found` | Wrong name/path | Must be exactly `%APPDATA%\TRAKKOUT\client_secrets.json` |
| `not valid JSON` / no `installed` section | Wrong JSON | Re-download the **Desktop app** client (step 4) |
| `access_denied` / 403 error on login | Your email is not in Test users | Step 3.5: add it and retry |
| *"Google hasn't verified this app"* | Normal in Testing | Advanced → Go to TRAKKOUT → Continue |
| `YouTube Data API v3 is not enabled` | Missing step 2 | Library → Enable |
| `redirect_uri_mismatch` | Web-type client instead of Desktop | Create a new **Desktop app** client |
| `invalid_grant` / expired session | Revoked or expired token | Press Connect again (delete `token.json` if it persists) |
| `quota exhausted` | Daily quota used up | Wait until next day |
| Browser doesn't open | Port 8765 busy or no browser | Close whatever uses 8765; copy the URL into your browser |
| Publishes to the wrong channel | Active session ≠ chosen channel | Disconnect + reconnect picking that channel |

## 9. Security (read once)

- `client_secrets.json` and `token.json` are **your keys**: don't upload them to
  GitHub, don't paste them in chats, don't put them in the repo (`.gitignore`
  already excludes them).
- You can revoke access anytime at
  https://myaccount.google.com/permissions (look for *TRAKKOUT*) and delete
  `%APPDATA%\TRAKKOUT\token.json` to fully disconnect.
- Tokens in `logs/app.log` are redacted automatically.

## 10. Official references

- OAuth Desktop Apps: https://developers.google.com/youtube/v3/guides/auth/installed-apps
- Creating credentials: https://developers.google.com/workspace/guides/create-credentials
- OAuth clients: https://console.cloud.google.com/auth/clients
- Quotas: Cloud Console → APIs & Services → Quotas
