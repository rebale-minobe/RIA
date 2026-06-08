"""
RIA Answer Log Pivot Manager
answer_log_{subject}_pivot.csv を直接更新する

フォーマット:
page_num, chapter_title, workbook_ref, lesson_title,
section_code, q_label, answer, answer_yomi,
YYYY-MM-DD_maru, YYYY-MM-DD_batsu, ...
"""
import csv
import io
import base64
import requests
import streamlit as st
from datetime import datetime, timezone, timedelta

OWNER  = "rebale-minobe"
REPO   = "RIA"
BRANCH = "main"
_JST   = timezone(timedelta(hours=9))


def _today_jst() -> str:
    return datetime.now(_JST).strftime("%Y-%m-%d")


def _get_token():
    for key in ["GITHUB_PAT","github_pat","GH_TOKEN","gh_token","GITHUB_TOKEN","github_token"]:
        try:
            val = st.secrets.get(key)
            if val: return val
        except Exception:
            pass
    return ""


def _headers_json():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _pivot_path(subject_key: str) -> str:
    return f"data/answer_log_{subject_key}_pivot.csv"


def _api_url(subject_key: str) -> str:
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{_pivot_path(subject_key)}"


def _load_pivot_csv(subject_key: str) -> tuple[list[dict], list[str]]:
    """GitHubからpivot CSVを読み込む（rows, fieldnames）"""
    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github.v3.raw",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        r = requests.get(
            _api_url(subject_key) + f"?ref={BRANCH}",
            headers=headers, timeout=10
        )
        if r.status_code == 200 and r.text.strip():
            reader = csv.DictReader(io.StringIO(r.text))
            rows = list(reader)
            return rows, list(reader.fieldnames or [])
    except Exception:
        pass
    return [], []


def _get_sha(subject_key: str) -> str | None:
    try:
        r = requests.get(
            _api_url(subject_key) + f"?ref={BRANCH}",
            headers=_headers_json(), timeout=10
        )
        if r.status_code == 200:
            return r.json().get("sha")
    except Exception:
        pass
    return None


def _push_pivot_csv(subject_key: str, rows: list[dict], fieldnames: list[str], message: str) -> bool:
    """pivot CSVをGitHubにpush"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    b64 = base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")

    sha = _get_sha(subject_key)
    body = {"message": message, "content": b64, "branch": BRANCH}
    if sha:
        body["sha"] = sha

    r = requests.put(_api_url(subject_key), headers=_headers_json(), json=body, timeout=30)
    if r.status_code in (200, 201):
        return True
    if r.status_code == 409:
        body["sha"] = _get_sha(subject_key)
        r = requests.put(_api_url(subject_key), headers=_headers_json(), json=body, timeout=30)
        if r.status_code in (200, 201):
            return True
    return False


def append_pivot_log(subject_key: str, q_data: dict, result: str) -> bool:
    """
    pivot CSVの該当行に今日の日付のマル/バツを記録

    q_data には以下が必要:
      page_num, section_code, q_label (または q), answer (または a)

    result: "maru" or "batsu"
    """
    today = _today_jst()
    col_name = f"{today}_{'maru' if result == 'maru' else 'batsu'}"

    rows, fieldnames = _load_pivot_csv(subject_key)
    if not rows:
        return False

    # 日付列を追加（なければ）
    if col_name not in fieldnames:
        # answer_yomi の後に挿入
        if "answer_yomi" in fieldnames:
            idx = fieldnames.index("answer_yomi") + 1
        else:
            idx = len(fieldnames)
        fieldnames.insert(idx, col_name)
        for r in rows:
            r[col_name] = ""

    # 該当行を特定してカウントアップ
    page_num  = str(q_data.get("page_num", q_data.get("page_number", "")))
    sec_code  = str(q_data.get("section_code", ""))
    q_label   = str(q_data.get("q_label", q_data.get("q", "")))
    answer    = str(q_data.get("answer", q_data.get("a", "")))

    matched = False
    for row in rows:
        # マッチ条件：page_num + section_code + q_label
        # q_labelが空の場合はanswerでも照合
        if (str(row.get("page_num","")) == page_num and
            str(row.get("section_code","")) == sec_code and
            (str(row.get("q_label","")) == q_label or
             str(row.get("answer","")) == answer)):
            current = row.get(col_name, "") or "0"
            try:
                row[col_name] = str(int(current) + 1)
            except ValueError:
                row[col_name] = "1"
            matched = True
            break

    if not matched:
        # 行が見つからない場合は新規追加
        new_row = {f: "" for f in fieldnames}
        new_row.update({
            "page_num": page_num,
            "section_code": sec_code,
            "q_label": q_label,
            "answer": answer,
            col_name: "1",
        })
        rows.append(new_row)
        fieldnames = list(new_row.keys())

    return _push_pivot_csv(
        subject_key, rows, fieldnames,
        f"[{subject_key}] {result}: p{page_num} {sec_code} {q_label}"
    )
