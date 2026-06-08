"""RIA Answer Log Pivot Manager v2026-06-08.1"""
ALM_PIVOT_VERSION = "v2026-06-08.1"

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


def _today_jst():
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


def _pivot_path(subject_key):
    return f"data/answer_log_{subject_key}_pivot.csv"


def _api_url(subject_key):
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{_pivot_path(subject_key)}"


def _load_pivot_csv(subject_key):
    """GitHubからpivot CSVを読み込む"""
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


def _get_sha(subject_key):
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


def _push_pivot_csv(subject_key, rows, fieldnames, message):
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


def append_pivot_log(subject_key, q_data, result):
    """pivot CSVの該当行に今日の日付のmaru/batsuを記録"""
    today = _today_jst()
    col_name = f"{today}_maru" if result == "maru" else f"{today}_batsu"

    rows, fieldnames = _load_pivot_csv(subject_key)
    if not rows:
        return False

    # 日付列を追加
    if col_name not in fieldnames:
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
        new_row = {f: "" for f in fieldnames}
        new_row.update({
            "page_num": page_num,
            "section_code": sec_code,
            "q_label": q_label,
            "answer": answer,
            col_name: "1",
        })
        rows.append(new_row)

    return _push_pivot_csv(
        subject_key, rows, fieldnames,
        f"[{subject_key}] {result}: p{page_num} {sec_code} {q_label}"
    )
