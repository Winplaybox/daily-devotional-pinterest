"""Pinterest API v5 client for listing boards, auto-refreshing tokens, and publishing Pins."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import set_key
import requests

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _base_url() -> str:
    if os.getenv("PINTEREST_SANDBOX", "false").strip().lower() in ("1", "true", "yes"):
        return "https://api-sandbox.pinterest.com/v5"
    return "https://api.pinterest.com/v5"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def refresh_access_token() -> str | None:
    """Refresh Pinterest OAuth access token using PINTEREST_REFRESH_TOKEN if configured."""
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN", "").strip()
    app_id = os.getenv("PINTEREST_APP_ID", "").strip()
    app_secret = os.getenv("PINTEREST_APP_SECRET", "").strip()
    if not (refresh_token and app_id and app_secret):
        return None

    basic = base64.b64encode(f"{app_id}:{app_secret}".encode("utf-8")).decode("ascii")
    resp = requests.post(
        f"{_base_url()}/oauth/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    if not resp.ok:
        return None

    data = resp.json()
    new_token = data.get("access_token", "").strip()
    if new_token:
        os.environ["PINTEREST_ACCESS_TOKEN"] = new_token
        if _ENV_PATH.exists():
            set_key(str(_ENV_PATH), "PINTEREST_ACCESS_TOKEN", new_token)
            if data.get("refresh_token"):
                set_key(str(_ENV_PATH), "PINTEREST_REFRESH_TOKEN", data["refresh_token"])
        return new_token
    return None


def _request_with_refresh(method: str, path: str, token: str, **kwargs) -> requests.Response:
    url = f"{_base_url()}{path}"
    resp = requests.request(method, url, headers=_headers(token), **kwargs)
    if resp.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            resp = requests.request(method, url, headers=_headers(new_token), **kwargs)
    return resp


def list_boards(access_token: str | None = None) -> list[dict]:
    """Fetch the authenticated user's Pinterest boards."""
    token = (access_token or os.getenv("PINTEREST_ACCESS_TOKEN", "")).strip()
    if not token or token == "your_pinterest_oauth_access_token_here":
        raise RuntimeError("PINTEREST_ACCESS_TOKEN is not set. Run 'python setup_pinterest.py' first.")

    resp = _request_with_refresh("GET", "/boards", token, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Pinterest API error ({resp.status_code}): {resp.text}")
    return resp.json().get("items", [])


def publish_pin(
    image_path: Path,
    board_id: str,
    title: str,
    description: str,
    alt_text: str = "",
    link: str = "",
    access_token: str | None = None,
) -> dict:
    """Publish a PNG image as a Pin on Pinterest using API v5 image_base64."""
    token = (access_token or os.getenv("PINTEREST_ACCESS_TOKEN", "")).strip()
    if not token or token == "your_pinterest_oauth_access_token_here":
        raise RuntimeError("PINTEREST_ACCESS_TOKEN is not set. Run 'python setup_pinterest.py' first.")
    if not board_id or board_id == "your_pinterest_board_id_here":
        raise RuntimeError("PINTEREST_BOARD_ID is not set. Run 'python setup_pinterest.py' first.")

    image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload: dict = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:800],
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": image_b64,
        },
    }
    if alt_text:
        payload["alt_text"] = alt_text[:500]
    if link:
        payload["link"] = link

    resp = _request_with_refresh("POST", "/pins", token, json=payload, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Pinterest publish failed ({resp.status_code}): {resp.text}")
    return resp.json()
