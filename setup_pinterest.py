"""One-click Pinterest OAuth login & automatic board/token setup script."""

from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

from dotenv import load_dotenv, set_key
import requests

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.example"
REDIRECT_URI = "http://localhost:8085/callback"
SCOPES = "boards:read,boards:write,pins:read,pins:write"


def _api_base() -> str:
    if os.getenv("PINTEREST_SANDBOX", "false").strip().lower() in ("1", "true", "yes"):
        return "https://api-sandbox.pinterest.com/v5"
    return "https://api.pinterest.com/v5"


def _ensure_env_file() -> None:
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
        else:
            ENV_PATH.write_text("", encoding="utf-8")


def _prompt_if_missing(key: str, label: str, required: bool = True) -> str:
    val = os.getenv(key, "").strip()
    if val and not val.startswith("your_"):
        return val
    while True:
        entered = input(f"Enter {label}: ").strip()
        if entered or not required:
            return entered
        print(f"  {label} cannot be empty.")


def _wait_for_oauth_code(auth_url: str) -> str:
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = parse_qs(parsed.query)
            if "code" in params:
                result["code"] = params["code"][0]
                body = b"<h2>Pinterest connected!</h2><p>You can close this tab and return to the terminal.</p>"
                self.send_response(200)
            else:
                result["error"] = params.get("error", ["Authorization failed"])[0]
                body = f"<h2>Error: {result['error']}</h2>".encode("utf-8")
                self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 8085), CallbackHandler)
    print(f"\nOpening browser for Pinterest login...\nIf it does not open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()

    if "error" in result:
        raise RuntimeError(f"Pinterest OAuth error: {result['error']}")
    return result["code"]


def _exchange_code(app_id: str, app_secret: str, code: str) -> dict:
    basic = base64.b64encode(f"{app_id}:{app_secret}".encode("utf-8")).decode("ascii")
    resp = requests.post(
        f"{_api_base()}/oauth/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text}")
    return resp.json()


def _fetch_or_create_board(access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.get(f"{_api_base()}/boards", headers=headers, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Failed to list boards ({resp.status_code}): {resp.text}")

    boards = resp.json().get("items", [])
    if boards:
        print("\nYour Pinterest Boards:")
        for idx, b in enumerate(boards, start=1):
            print(f"  {idx}. {b.get('name')} (ID: {b.get('id')})")
        print("  C. Create a new board")
        choice = input("\nSelect board number (or C to create new) [1]: ").strip() or "1"
        if choice.lower() != "c":
            idx = int(choice) - 1
            if 0 <= idx < len(boards):
                return boards[idx]["id"]

    board_name = input("New board name [Daily Devotional Blessings]: ").strip() or "Daily Devotional Blessings"
    create_resp = requests.post(
        f"{_api_base()}/boards",
        headers=headers,
        json={
            "name": board_name,
            "description": "Daily devotional god images with date and blessings.",
            "privacy": "PUBLIC",
        },
        timeout=30,
    )
    if not create_resp.ok:
        raise RuntimeError(f"Failed to create board ({create_resp.status_code}): {create_resp.text}")
    new_board = create_resp.json()
    print(f"Created board '{new_board.get('name')}' (ID: {new_board.get('id')})")
    return new_board["id"]


def main() -> int:
    _ensure_env_file()
    load_dotenv(ENV_PATH)

    print("=== Pinterest Auto-Setup ===")
    print("Note: In your Pinterest App settings (developers.pinterest.com),")
    print(f"add this Redirect URI: {REDIRECT_URI}\n")

    app_id = _prompt_if_missing("PINTEREST_APP_ID", "Pinterest App ID")
    app_secret = _prompt_if_missing("PINTEREST_APP_SECRET", "Pinterest App Secret")
    gemini_key = _prompt_if_missing("GEMINI_API_KEY", "Gemini API Key (optional, press Enter to skip)", required=False)

    set_key(str(ENV_PATH), "PINTEREST_APP_ID", app_id)
    set_key(str(ENV_PATH), "PINTEREST_APP_SECRET", app_secret)
    if gemini_key:
        set_key(str(ENV_PATH), "GEMINI_API_KEY", gemini_key)

    params = urlencode({
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    })
    auth_url = f"https://www.pinterest.com/oauth/?{params}"
    code = _wait_for_oauth_code(auth_url)

    tokens = _exchange_code(app_id, app_secret, code)
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token", "")

    set_key(str(ENV_PATH), "PINTEREST_ACCESS_TOKEN", access_token)
    if refresh_token:
        set_key(str(ENV_PATH), "PINTEREST_REFRESH_TOKEN", refresh_token)

    board_id = _fetch_or_create_board(access_token)
    set_key(str(ENV_PATH), "PINTEREST_BOARD_ID", board_id)

    print("\nAll saved to .env! You can now run:")
    print("  python main.py --publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
