"""期末テスト・学習計画のデータ管理"""
import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SCHEDULE_PATH = DATA_DIR / "schedule.json"


def load_schedule() -> dict:
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(data: dict) -> None:
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_test() -> dict | None:
    data = load_schedule()
    tid = data.get("current_test_id")
    for t in data.get("tests", []):
        if t["id"] == tid:
            return t
    return None


def get_days_until_test() -> int | None:
    test = get_current_test()
    if not test:
        return None
    start = datetime.strptime(test["start_date"], "%Y-%m-%d").date()
    return (start - date.today()).days


def get_subject_range(subject_key: str) -> dict | None:
    test = get_current_test()
    if not test:
        return None
    for s in test.get("subjects", []):
        if s.get("subject_key") == subject_key:
            return s
    return None


def get_today_tasks() -> list:
    test = get_current_test()
    if not test:
        return []
    today_str = date.today().isoformat()
    for d in test.get("study_plan", []):
        if d.get("date") == today_str:
            return d.get("tasks", [])
    return []


def mark_task_done(date_str: str, idx: int, done: bool = True) -> None:
    data = load_schedule()
    test = next(t for t in data["tests"] if t["id"] == data["current_test_id"])
    for d in test["study_plan"]:
        if d["date"] == date_str:
            d["tasks"][idx]["done"] = done
            break
    save_schedule(data)


def get_progress_summary() -> dict:
    """全体の進捗サマリー"""
    test = get_current_test()
    if not test:
        return {"total": 0, "done": 0, "percent": 0}
    total = sum(len(d.get("tasks", [])) for d in test.get("study_plan", []))
    done = sum(
        1 for d in test.get("study_plan", [])
        for t in d.get("tasks", []) if t.get("done")
    )
    percent = round(100 * done / total) if total else 0
    return {"total": total, "done": done, "percent": percent}
