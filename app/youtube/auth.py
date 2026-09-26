"""OAuth 2.0 with Google for YouTube Data API v3. No hardcoded secrets."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

REDIRECT_PORT = 8765


class OAuthConfigError(RuntimeError):
    pass


class OAuthCancelledError(RuntimeError):
    pass


def _require_google_libs():
    try:
        from google.auth.transport.requests import Request  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
    except ImportError as exc:
        raise OAuthConfigError(
                "Missing Google libraries (google-auth, google-auth-oauthlib).\n"
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc


def _has_oauth_section(data: object) -> bool:
    return isinstance(data, dict) and ("installed" in data or "web" in data)


def find_client_secrets_file(search_dir: str | Path) -> Path | None:
    """Locate the OAuth client JSON in the app data dir.

    Google downloads it with names like
    ``client_secret_<id>.apps.googleusercontent.com.json``, so renaming to
    ``client_secrets.json`` is optional: the exact name wins when present,
    otherwise the first structurally valid ``client_secret*.json`` is used.
    """
    directory = Path(search_dir)
    exact = directory / "client_secrets.json"
    if exact.is_file():
        return exact
    for candidate in sorted(directory.glob("client_secret*.json")):
        if candidate == exact or not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _has_oauth_section(data):
            return candidate
    return None


class GoogleAuth:
    """Manages the OAuth client JSON + token.json (with automatic refresh)."""

    def __init__(self, client_secrets_path: str | Path, token_path: str | Path) -> None:
        self.client_secrets_path = Path(client_secrets_path)
        self.token_path = Path(token_path)

    # ---- state ----
    def effective_secrets_path(self) -> Path:
        """Configured path, or an auto-detected client_secret*.json next to it."""
        if self.client_secrets_path.is_file():
            return self.client_secrets_path
        found = find_client_secrets_file(self.client_secrets_path.parent)
        return found or self.client_secrets_path

    def validate_client_secrets(self) -> tuple[bool, str]:
        p = self.effective_secrets_path()
        if not p.is_file():
            return False, (
                "OAuth client JSON not found.\n"
                f"Looked in: {p.parent}\n\n"
                "Create OAuth credentials (Desktop app) in Google Cloud Console and "
                "drop the downloaded file there (any client_secret*.json name works; "
                "renaming it to client_secrets.json is optional). "
                "See README section 5."
            )
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"{p.name} is not valid JSON: {exc}"
        if not _has_oauth_section(data):
            return False, (
                f"{p.name} has neither an 'installed' nor a 'web' section.\n"
                "Re-download 'Desktop app' OAuth credentials."
            )
        return True, f"{p.name} is valid."

    def load_credentials(self):
        """Return valid Credentials (refreshing if needed) or None."""
        _require_google_libs()
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        if not self.token_path.exists():
            return None
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        except Exception as exc:
            log.warning("token.json unreadable: %s", exc)
            return None
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_credentials(creds)
            except Exception as exc:
                log.warning("Could not refresh token: %s", exc)
                return None
        if creds and creds.valid:
            return creds
        return None

    def save_credentials(self, creds) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        try:
            # Restrictive permissions where possible (no real effect on Windows, but harmless).
            import os
            os.chmod(self.token_path, 0o600)
        except Exception:
            pass

    def run_consent_flow(self):
        """Open the browser for OAuth consent. Raise OAuthCancelledError if cancelled."""
        _require_google_libs()
        from google_auth_oauthlib.flow import InstalledAppFlow

        ok, msg = self.validate_client_secrets()
        if not ok:
            raise OAuthConfigError(msg)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.effective_secrets_path()), SCOPES)
            creds = flow.run_local_server(
                port=REDIRECT_PORT,
                open_browser=True,
                prompt="consent",
                include_granted_scopes="true",
            )
        except FileNotFoundError as exc:
            raise OAuthConfigError(f"OAuth client JSON not found: {exc}") from exc
        except Exception as exc:
            text = str(exc).lower()
            if "cancel" in text or "access_denied" in text or "denied by user" in text:
                raise OAuthCancelledError("Authorization cancelled by the user in Google.") from exc
            raise OAuthConfigError(f"Could not complete Google login: {exc}") from exc
        self.save_credentials(creds)
        return creds

    def disconnect(self) -> None:
        """Delete the local token (best-effort revocation, non-blocking)."""
        try:
            if self.token_path.exists():
                self.token_path.unlink()
        except Exception as exc:
            log.warning("Could not delete token.json: %s", exc)
