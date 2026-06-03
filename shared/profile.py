"""学習者プロファイル読み込み"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class Profile:
    def __init__(self, data: dict):
        self.data = data

    def get_summary_text(self) -> str:
        """システムプロンプトに注入するサマリーテキスト"""
        d = self.data
        lines = [
            f"- 名前: {d['name']}（{d['grade']} {d['class']}）",
            f"- 部活: {d['club']}",
            f"- 将来の夢: {d['dream']}",
            f"- タイプ: {d['type_diagnosis']}",
            "",
            "【強み】",
            *[f"  ・{s}" for s in d['strengths']],
            "",
            "【伸びしろ】",
            *[f"  ・{g}" for g in d['growth_areas']],
            "",
            f"- 英語: {d['english']['level']}（次の目標: {d['english']['next_goal']}）",
            f"- 中1ベースライン: {d['baseline']['summary']}",
        ]
        return "\n".join(lines)

    def get_subject_baseline(self, subject_key: str) -> dict:
        """教科別の中1ベースラインを取得"""
        return self.data['baseline']['subjects'].get(subject_key, {})


def get_profile() -> Profile:
    path = DATA_DIR / "profile.json"
    with open(path, "r", encoding="utf-8") as f:
        return Profile(json.load(f))
