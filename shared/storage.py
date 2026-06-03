"""
データ永続化レイヤー
MVP: ローカルJSON
Phase 2: GitHub API + private repo (ria-data) に切替予定
"""
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
MISTAKES_DIR = DATA_DIR / "mistakes"
MISTAKES_DIR.mkdir(exist_ok=True)


def save_mistake(subject_key: str, question: str, ria_answer: str,
                 correct_answer: str, error_type: str = "") -> None:
    """間違いノートに1件保存"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "subject": subject_key,
        "question": question,
        "ria_answer": ria_answer,
        "correct_answer": correct_answer,
        "error_type": error_type,
    }
    file = MISTAKES_DIR / f"{subject_key}.json"
    items = []
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            items = json.load(f)
    items.append(record)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def load_mistakes(subject_key: str) -> list:
    """教科の間違いノート全件取得"""
    file = MISTAKES_DIR / f"{subject_key}.json"
    if not file.exists():
        return []
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)
