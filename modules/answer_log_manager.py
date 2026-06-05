"""
RIA Answer Log Manager v2
教科ごとに data/answer_log_{subject_key}.csv を GitHub に永続保存
"""
import csv, io, base64, requests, streamlit as st
from datetime import datetime

OWNER  = "rebale-minobe"
REPO   = "RIA"
BRANCH = "main"

CSV_HEADERS = [
    "date", "genre_key", "genre_name",
    "page_num", "workbook_ref", "lesson_title",
    "section_code", "section_name", "group_label",
    "q", "a", "result", "note"
]


def _csv_path(subject_key: str) -> str:
    return f"data/answer_log_{subject_key}.csv"


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


def _api_url(subject_key: str) -> str:
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{_csv_path(subject_key)}"


@st.cache_data(ttl=60)
def load_csv(subject_key: str) -> list:
    """GitHubからCSVを読み込んで辞書リストで返す"""
    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github.v3.raw",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        url = _api_url(subject_key) + f"?ref={BRANCH}"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and r.text.strip():
            reader = csv.DictReader(io.StringIO(r.text))
            return list(reader)
    except Exception:
        pass
    return []


def _get_sha(subject_key: str):
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


def _push_csv(subject_key: str, rows: list, message: str) -> bool:
    """CSVをGitHubにpush"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_HEADERS, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    b64 = base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")

    sha = _get_sha(subject_key)
    body = {"message": message, "content": b64, "branch": BRANCH}
    if sha:
        body["sha"] = sha

    for _ in range(2):
        r = requests.put(_api_url(subject_key), headers=_headers_json(), json=body, timeout=30)
        if r.status_code in (200, 201):
            load_csv.clear()
            return True
        if r.status_code == 409:
            body["sha"] = _get_sha(subject_key)
        else:
            break
    return False


def make_entry(question: dict, result: str) -> dict:
    """ログエントリを作成"""
    return {
        "date":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "genre_key":    question.get("genre_key", ""),
        "genre_name":   question.get("genre_name", ""),
        "page_num":     question.get("page_number", ""),
        "workbook_ref": question.get("workbook_ref", ""),
        "lesson_title": question.get("lesson_title", ""),
        "section_code": question.get("section_code", ""),
        "section_name": question.get("section_name", ""),
        "group_label":  question.get("group_label", ""),
        "q":            question.get("q", ""),
        "a":            question.get("a", ""),
        "result":       result,
        "note":         question.get("note", "") or "",
    }


def append_batch(subject_key: str, entries: list) -> bool:
    """複数件まとめてpush（バッチ）"""
    if not entries:
        return True
    rows = load_csv(subject_key)
    rows.extend(entries)
    return _push_csv(
        subject_key, rows,
        f"answer_log: {subject_key} +{len(entries)} entries"
    )


def get_batsu_questions(subject_key: str) -> list:
    """
    最新結果がbatsuの問題を返す
    同一問題（genre+page+q）の最新ログのみ参照
    """
    rows = load_csv(subject_key)
    if not rows:
        return []
    latest = {}
    for row in rows:
        key = (row.get("genre_key",""), str(row.get("page_num","")), row.get("q",""))
        latest[key] = row  # 追記型なので後勝ち＝最新
    return [v for v in latest.values() if v.get("result") == "batsu"]


def get_all_batsu_questions(subject_keys: list) -> list:
    """全教科のbatsu問題を取得"""
    result = []
    for skey in subject_keys:
        for row in get_batsu_questions(skey):
            row["subject_key"] = skey
            result.append(row)
    return result


def get_stats(subject_key: str) -> dict:
    """教科別の統計"""
    rows = load_csv(subject_key)
    total = len(rows)
    batsu = sum(1 for r in rows if r.get("result") == "batsu")
    maru  = sum(1 for r in rows if r.get("result") == "maru")
    # 単元別正答率
    by_lesson = {}
    for r in rows:
        lesson = r.get("lesson_title", "")
        if lesson not in by_lesson:
            by_lesson[lesson] = {"batsu": 0, "maru": 0, "total": 0}
        by_lesson[lesson][r.get("result", "batsu")] += 1
        by_lesson[lesson]["total"] += 1
    # 問題別正誤履歴
    by_q = {}
    for r in rows:
        key = (r.get("genre_key",""), str(r.get("page_num","")), r.get("q",""))
        if key not in by_q:
            by_q[key] = []
        by_q[key].append(r.get("result",""))
    return {
        "total": total, "batsu": batsu, "maru": maru,
        "accuracy": round(maru / total * 100, 1) if total else 0,
        "by_lesson": by_lesson,
        "by_q": by_q,
    }
