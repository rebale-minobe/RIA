"""GitHub Contents API helper for RIA
- 404 (新規ファイル) を SHA なしで PUT する処理に対応
"""
import os
import base64
import requests
import streamlit as st

OWNER = "MinobeHiroshi"
REPO = "RIA"
BRANCH = "main"


def _get_token():
    """Streamlit secrets から PAT を取得（複数のキー名にフォールバック）"""
    # Streamlit secrets を順番にチェック
    candidates = [
        "GITHUB_PAT", "github_pat",
        "GH_TOKEN", "gh_token",
        "GITHUB_TOKEN", "github_token",
    ]
    for key in candidates:
        try:
            val = st.secrets[key] if key in st.secrets else None
            if val:
                return val
        except Exception:
            continue
    # 環境変数フォールバック
    return (
        os.environ.get("GITHUB_PAT")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or ""
    )


def _headers_json():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _api_url(path: str) -> str:
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"


def gh_get_text(path: str) -> str | None:
    """ファイルをテキストで取得。存在しなければ None。"""
    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github.v3.raw",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = _api_url(path) + f"?ref={BRANCH}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
        if r.status_code == 404:
            return None
        # 200 で empty content の場合は raw fallback
        if r.status_code == 200 and not r.text:
            return None
    except Exception:
        pass
    return None


def _get_sha(path: str) -> str | None:
    """既存ファイルの SHA を取得。新規ファイル (404) の場合は None。"""
    url = _api_url(path) + f"?ref={BRANCH}"
    try:
        r = requests.get(url, headers=_headers_json(), timeout=15)
        if r.status_code == 200:
            return r.json().get("sha")
        # 404 = 新規ファイル → None を返す（エラーにしない）
        return None
    except Exception:
        return None


def gh_put(path: str, content_bytes: bytes, message: str, max_retry: int = 2):
    """ファイル新規作成または更新。
    - 新規ファイル (SHA = None) でも作成できる
    - 409 Conflict 時に SHA を再取得して再試行
    """
    url = _api_url(path)
    sha = _get_sha(path)

    for attempt in range(max_retry + 1):
        body = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode("ascii"),
            "branch": BRANCH,
        }
        if sha:
            body["sha"] = sha

        r = requests.put(url, headers=_headers_json(), json=body, timeout=60)

        # 成功
        if r.status_code in (200, 201):
            return r.json()

        # 409 Conflict (SHA 不一致) → SHA 再取得してリトライ
        if r.status_code == 409 and attempt < max_retry:
            sha = _get_sha(path)
            continue

        # その他のエラー
        r.raise_for_status()

    raise RuntimeError(f"gh_put failed after retries: {path}")
