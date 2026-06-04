"""GitHub Contents API ヘルパー（RIA用）.

Streamlit CloudからリポジトリにファイルをPUT/UPDATEするための薄いラッパ。
PAT は st.secrets['GITHUB_TOKEN'] に登録しておくこと。
"""
from __future__ import annotations
import base64
import requests
import streamlit as st

# --- 設定 ---------------------------------------------------------
OWNER  = "MinobeHiroshi"
REPO   = "RIA"           # ← 実リポジトリ名に合わせて変更
BRANCH = "main"

_API = "https://api.github.com"


def _hdr() -> dict:
    return {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def _get_sha(path: str) -> str | None:
    """ファイルが既に存在すれば sha を返す。無ければ None。"""
    url = f"{_API}/repos/{OWNER}/{REPO}/contents/{path}"
    r = requests.get(url, headers=_hdr(), params={"ref": BRANCH}, timeout=15)
    if r.status_code == 200:
        data = r.json()
        # 1MB超のファイルは配列で返るが、ここでは小さいJSON想定
        if isinstance(data, dict):
            return data.get("sha")
    return None


def gh_put(path: str, content_bytes: bytes, message: str) -> dict:
    """ファイルを作成 or 更新（Contents API）。

    既存ファイル更新時の 409 Conflict（sha 古い）には1度だけ自動リトライする。
    """
    url = f"{_API}/repos/{OWNER}/{REPO}/contents/{path}"

    def _put(sha: str | None) -> requests.Response:
        body = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode(),
            "branch": BRANCH,
        }
        if sha:
            body["sha"] = sha
        return requests.put(url, headers=_hdr(), json=body, timeout=20)

    sha = _get_sha(path)
    r = _put(sha)

    # 409 や 422（sha競合）は最新shaで1度だけリトライ
    if r.status_code in (409, 422):
        sha = _get_sha(path)
        r = _put(sha)

    r.raise_for_status()
    return r.json()


def gh_get_text(path: str) -> str | None:
    """ファイル内容を文字列で取得。存在しなければ None。"""
    url = f"{_API}/repos/{OWNER}/{REPO}/contents/{path}"
    r = requests.get(url, headers=_hdr(), params={"ref": BRANCH}, timeout=15)
    if r.status_code != 200:
        return None
    data = r.json()
    if isinstance(data, dict) and data.get("content"):
        return base64.b64decode(data["content"]).decode("utf-8")
    # >1MB 等の場合は raw API でフォールバック
    raw = requests.get(
        f"{_API}/repos/{OWNER}/{REPO}/contents/{path}",
        headers={**_hdr(), "Accept": "application/vnd.github.raw"},
        params={"ref": BRANCH},
        timeout=20,
    )
    return raw.text if raw.status_code == 200 else None
