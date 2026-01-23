import base64
import hashlib
import json
import os
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TypedDict, Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from python.helpers import files
from python.helpers.print_style import PrintStyle


CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"

AUTH_FILE = "tmp/openai_auth.json"


class OpenAIAuth(TypedDict):
    access_token: str
    refresh_token: str
    expires_at: int
    account_id: str | None


class AuthorizationFlow(TypedDict):
    state: str
    verifier: str
    url: str


_pending_lock = threading.Lock()
_pending_flow: AuthorizationFlow | None = None
_callback_server: ThreadingHTTPServer | None = None
_callback_thread: threading.Thread | None = None


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _build_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = _base64url(digest)
    return verifier, challenge


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode()).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


def _extract_account_id(access_token: str) -> str | None:
    payload = _decode_jwt_payload(access_token) or {}
    auth_claim = payload.get("https://api.openai.com/auth") or {}
    if isinstance(auth_claim, dict):
        return auth_claim.get("chatgpt_account_id")
    return None


def _load_auth_file() -> OpenAIAuth | None:
    abs_path = files.get_abs_path(AUTH_FILE)
    if not os.path.exists(abs_path):
        return None
    try:
        content = files.read_file(AUTH_FILE)
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = data.get("expires_at")
        if not access_token or not refresh_token or not isinstance(expires_at, (int, float)):
            return None
        return OpenAIAuth(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=int(expires_at),
            account_id=data.get("account_id"),
        )
    except Exception:
        return None


def _save_auth_file(auth: OpenAIAuth) -> None:
    files.write_file(AUTH_FILE, json.dumps(auth, indent=2))


def clear_auth() -> None:
    abs_path = files.get_abs_path(AUTH_FILE)
    if os.path.exists(abs_path):
        os.remove(abs_path)


def get_auth_status() -> dict[str, Any]:
    auth = _load_auth_file()
    now = int(time.time() * 1000)
    if not auth:
        return {
            "connected": False,
            "expired": False,
            "has_token": False,
            "expires_at": None,
            "account_id": None,
        }
    expired = auth["expires_at"] <= now
    return {
        "connected": not expired,
        "expired": expired,
        "has_token": True,
        "expires_at": auth["expires_at"],
        "account_id": auth.get("account_id"),
    }


def create_authorization_flow() -> AuthorizationFlow:
    verifier, challenge = _build_pkce_pair()
    state = secrets.token_hex(16)

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "codex_cli_rs",
    }
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"
    return AuthorizationFlow(state=state, verifier=verifier, url=url)


def set_pending_flow(flow: AuthorizationFlow) -> None:
    with _pending_lock:
        global _pending_flow
        _pending_flow = flow


def _consume_pending_flow() -> AuthorizationFlow | None:
    with _pending_lock:
        global _pending_flow
        flow = _pending_flow
        _pending_flow = None
        return flow


def _peek_pending_flow() -> AuthorizationFlow | None:
    with _pending_lock:
        return _pending_flow


def exchange_authorization_code(code: str, verifier: str) -> OpenAIAuth | None:
    response = httpx.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15.0,
    )
    if response.status_code != HTTPStatus.OK:
        PrintStyle.error(
            f"OpenAI OAuth token exchange failed: {response.status_code} {response.text}"
        )
        return None

    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    if not access_token or not refresh_token or not isinstance(expires_in, (int, float)):
        PrintStyle.error("OpenAI OAuth token response missing fields.")
        return None

    account_id = _extract_account_id(access_token)
    return OpenAIAuth(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(time.time() * 1000 + float(expires_in) * 1000),
        account_id=account_id,
    )


SUCCESS_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>OpenAI Auth Complete</title>
    <style>
      body {
        font-family: system-ui, -apple-system, Segoe UI, sans-serif;
        background: #0f1115;
        color: #e6e6e6;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        margin: 0;
        text-align: center;
      }
      .card {
        background: #1a1d24;
        border: 1px solid #2d313b;
        border-radius: 12px;
        padding: 32px;
        max-width: 420px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
      }
      h1 {
        font-size: 20px;
        margin: 0 0 12px;
      }
      p {
        color: #b9c0cf;
        margin: 0;
      }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Authentication successful</h1>
      <p>You can close this tab and return to Agent Zero.</p>
    </div>
  </body>
</html>
"""


ERROR_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>OpenAI Auth Failed</title>
    <style>
      body {
        font-family: system-ui, -apple-system, Segoe UI, sans-serif;
        background: #111216;
        color: #f6f6f6;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        margin: 0;
        text-align: center;
      }
      .card {
        background: #1b1f26;
        border: 1px solid #3a3f4d;
        border-radius: 12px;
        padding: 32px;
        max-width: 420px;
      }
      h1 {
        font-size: 20px;
        margin: 0 0 12px;
      }
      p {
        color: #c4c9d6;
        margin: 0;
      }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Authentication failed</h1>
      <p>Return to Agent Zero and try signing in again.</p>
    </div>
  </body>
</html>
"""


class _CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/auth/callback":
            self._send_text(HTTPStatus.NOT_FOUND, "Not found")
            return

        params = parse_qs(parsed.query)
        code = (params.get("code") or [None])[0]
        state = (params.get("state") or [None])[0]

        flow = _peek_pending_flow()
        if not flow or not state or state != flow["state"]:
            self._send_html(HTTPStatus.BAD_REQUEST, ERROR_HTML)
            return
        if not code:
            self._send_html(HTTPStatus.BAD_REQUEST, ERROR_HTML)
            return

        _consume_pending_flow()
        auth = exchange_authorization_code(code, flow["verifier"])
        if not auth:
            self._send_html(HTTPStatus.BAD_REQUEST, ERROR_HTML)
            return

        _save_auth_file(auth)
        PrintStyle().print("OpenAI OAuth completed. Tokens stored.")
        self._send_html(HTTPStatus.OK, SUCCESS_HTML)

    def _send_text(self, status: HTTPStatus, text: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def _send_html(self, status: HTTPStatus, html: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def ensure_callback_server() -> None:
    global _callback_server, _callback_thread
    if _callback_server:
        return

    try:
        _callback_server = ThreadingHTTPServer(("127.0.0.1", 1455), _CallbackHandler)
    except OSError as exc:
        PrintStyle.error(f"OpenAI OAuth callback server unavailable: {exc}")
        _callback_server = None
        return

    _callback_thread = threading.Thread(
        target=_callback_server.serve_forever, daemon=True
    )
    _callback_thread.start()
