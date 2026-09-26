"""Tests for YouTube error mapping and OAuth config validation (no network)."""
from __future__ import annotations

import json
from pathlib import Path

from app.youtube.auth import GoogleAuth
from app.youtube.errors import explain_http_error


def _payload(reason: str, message: str = "boom") -> str:
    return json.dumps({"error": {"message": message, "errors": [{"reason": reason}]}})


def test_explain_401_session():
    err = explain_http_error(401, _payload("authError"), "default")
    assert err.code == 401
    assert "Reconnect" in err.user_message


def test_explain_quota_exhausted():
    err = explain_http_error(403, _payload("quotaExceeded"), "default")
    assert "quota" in err.user_message.lower()


def test_explain_api_not_enabled():
    err = explain_http_error(403, _payload("accessNotConfigured"), "default")
    assert "not enabled" in err.user_message


def test_explain_insufficient_permissions():
    err = explain_http_error(403, _payload("insufficientPermissions"), "default")
    assert "permissions" in err.user_message.lower()


def test_explain_forbidden_not_found_server_and_default():
    assert "permission" in explain_http_error(403, _payload("forbidden"), "d").user_message.lower()
    assert "not found" in explain_http_error(404, _payload("notFound"), "d").user_message.lower()
    assert "Retry" in explain_http_error(500, _payload("backendError"), "d").user_message
    fallback = explain_http_error(400, _payload("unknownReason", "detail-here"), "Upload failed")
    assert "Upload failed" in fallback.user_message
    assert "detail-here" in fallback.user_message


def test_explain_invalid_json_keeps_content():
    err = explain_http_error(400, b"not json at all", "Upload failed")
    assert "Upload failed" in err.user_message


def test_oauth_missing_file(tmp_path: Path):
    auth = GoogleAuth(tmp_path / "client_secrets.json", tmp_path / "token.json")
    ok, msg = auth.validate_client_secrets()
    assert ok is False
    assert "not found" in msg


def test_oauth_invalid_json(tmp_path: Path):
    secrets = tmp_path / "client_secrets.json"
    secrets.write_text("{broken", encoding="utf-8")
    ok, msg = GoogleAuth(secrets, tmp_path / "token.json").validate_client_secrets()
    assert ok is False
    assert "valid JSON" in msg


def test_oauth_wrong_section(tmp_path: Path):
    secrets = tmp_path / "client_secrets.json"
    secrets.write_text(json.dumps({"other": {}}), encoding="utf-8")
    ok, _ = GoogleAuth(secrets, tmp_path / "token.json").validate_client_secrets()
    assert ok is False


def test_oauth_valid_installed_section(tmp_path: Path):
    secrets = tmp_path / "client_secrets.json"
    secrets.write_text(json.dumps({"installed": {"client_id": "x"}}), encoding="utf-8")
    ok, _ = GoogleAuth(secrets, tmp_path / "token.json").validate_client_secrets()
    assert ok is True


def test_oauth_detects_google_download_name(tmp_path: Path):
    dl = tmp_path / "client_secret_872538482962-abc123.apps.googleusercontent.com.json"
    dl.write_text(json.dumps({"installed": {"client_id": "x"}}), encoding="utf-8")
    auth = GoogleAuth(tmp_path / "client_secrets.json", tmp_path / "token.json")
    assert auth.effective_secrets_path() == dl
    ok, msg = auth.validate_client_secrets()
    assert ok is True
    assert dl.name in msg


def test_oauth_exact_name_wins_over_download(tmp_path: Path):
    exact = tmp_path / "client_secrets.json"
    exact.write_text(json.dumps({"installed": {"client_id": "exact"}}), encoding="utf-8")
    dl = tmp_path / "client_secret_123.json"
    dl.write_text(json.dumps({"installed": {"client_id": "other"}}), encoding="utf-8")
    auth = GoogleAuth(exact, tmp_path / "token.json")
    assert auth.effective_secrets_path() == exact
    ok, _ = auth.validate_client_secrets()
    assert ok is True


def test_oauth_ignores_invalid_downloads(tmp_path: Path):
    bad = tmp_path / "client_secret_broken.json"
    bad.write_text("{not json", encoding="utf-8")
    auth = GoogleAuth(tmp_path / "client_secrets.json", tmp_path / "token.json")
    ok, msg = auth.validate_client_secrets()
    assert ok is False
    assert "not found" in msg
