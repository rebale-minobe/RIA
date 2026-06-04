"""
解答ログ管理モジュール
- data/answer_log.json に GitHub 経由で永続化
- 「最新の解答結果が ✕ の問題」を未解決問題として取得
- 教科横断・反復出題のためのデータ基盤
"""
import json
from datetime import datetime
from modules.gh import gh_put, gh_get_text

LOG_PATH = "data/answer_log.json"


def load_logs() -> list:
    """全ログを読み込む（GitHub から取得）"""
    try:
        text = gh_get_text(LOG_PATH)
        if text:
            data = json.loads(text)
            return data.get("logs", [])
    except Exception:
        pass
    return []


def append_log(entry: dict) -> bool:
    """ログを1件追記して GitHub に push"""
    logs = load_logs()
    logs.append(entry)
    body = json.dumps({"logs": logs}, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        gh_put(LOG_PATH, body, f"Answer log: {entry.get('q','')} ({entry.get('result','')})")
        return True
    except Exception:
        return False


def _question_key(log: dict) -> tuple:
    """問題の一意キー（教科+ジャンル+ページ+セクション+グループ+問題番号）"""
    return (
        log.get("subject_key"),
        log.get("genre_key"),
        log.get("workbook_page"),
        log.get("section_code"),
        log.get("group_label"),
        log.get("q"),
    )


def get_unsolved_questions() -> list:
    """最新の解答結果が ✕ の問題を返す（教科横断）"""
    logs = load_logs()
    latest = {}
    for log in logs:
        latest[_question_key(log)] = log
    return [log for log in latest.values() if log.get("result") == "batsu"]


def get_stats() -> dict:
    """統計情報"""
    logs = load_logs()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = [l for l in logs if l.get("date") == today_str]

    latest = {}
    for log in logs:
        latest[_question_key(log)] = log

    return {
        "total_attempts": len(logs),
        "unique_questions": len(latest),
        "currently_correct": sum(1 for l in latest.values() if l.get("result") == "maru"),
        "currently_wrong": sum(1 for l in latest.values() if l.get("result") == "batsu"),
        "today_attempts": len(today_logs),
        "today_correct": sum(1 for l in today_logs if l.get("result") == "maru"),
        "today_wrong": sum(1 for l in today_logs if l.get("result") == "batsu"),
    }


def question_to_log_entry(
    question_data: dict,
    subject_key: str, subject_name: str,
    genre_key: str, genre_name: str,
    result: str,
) -> dict:
    """フラッシュカードの問題データから log entry を作成"""
    now = datetime.now()
    return {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "subject_key": subject_key,
        "subject_name": subject_name,
        "genre_key": genre_key,
        "genre_name": genre_name,
        "workbook_page": question_data.get("page_number"),
        "lesson_title": question_data.get("lesson_title", ""),
        "chapter_title": question_data.get("chapter_title", ""),
        "section_code": question_data.get("section_code"),
        "section_name": question_data.get("section_name"),
        "textbook_ref": question_data.get("textbook_ref"),
        "group_label": question_data.get("group_label"),
        "q": question_data.get("q"),
        "a": question_data.get("a"),
        "note": question_data.get("note"),
        "context": question_data.get("context"),
        "result": result,
    }


def log_to_question(log: dict) -> dict:
    """log entry をフラッシュカード用の question dict に変換"""
    return {
        "page_number": log.get("workbook_page"),
        "lesson_title": log.get("lesson_title", ""),
        "chapter_title": log.get("chapter_title", ""),
        "section_code": log.get("section_code"),
        "section_name": log.get("section_name"),
        "textbook_ref": log.get("textbook_ref"),
        "group_label": log.get("group_label"),
        "q": log.get("q"),
        "a": log.get("a"),
        "note": log.get("note"),
        "context": log.get("context"),
        "subject_key": log.get("subject_key"),
        "subject_name": log.get("subject_name"),
        "genre_key": log.get("genre_key"),
        "genre_name": log.get("genre_name"),
    }
