"""
RIA Study Agent v1.0
問題スクショから自動で類題を生成・解説を提供

claude_client.py と統合（get_client / MODEL を再利用）
配置先: modules/study_agent.py
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# プロジェクト共通の Claude クライアントを再利用
from shared.claude_client import get_client, MODEL

_JST = timezone(timedelta(hours=9))
def _now_jst():
    return datetime.now(_JST).replace(tzinfo=None)


def _extract_json(response_text: str):
    """Claude の応答から JSON を抽出（```json ... ``` 対応）"""
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    return json.loads(json_str)


def extract_problem_from_image(image_base64: str, image_media_type: str = "image/jpeg") -> dict:
    """
    スクショから問題文を自動抽出

    Returns:
        {"problem_text": str, "chapter": str, "success": bool}
    """
    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": """このスクショに写っている数学の問題文を正確に抽出してください。

以下の JSON 形式で返してください（日本語で）：
{
  "problem_text": "問題文",
  "chapter": "推定される章（例：2年-第1章-式の計算）",
  "confidence": 0.95
}

問題が写っていない場合は confidence: 0 を返してください。"""
                }
            ]
        }]
    )

    try:
        result = _extract_json(message.content[0].text)
        result["success"] = result.get("confidence", 0) > 0.5
        return result
    except Exception as e:
        return {"problem_text": "", "chapter": "", "success": False, "error": str(e)}


def generate_practice_problems(problem_text: str, chapter: str = "", textbook_reference: str = "2年教科書 P11-34") -> list:
    """
    元の問題から 3 段階の類題を自動生成（基本・標準・応用）

    Returns:
        [{"id", "problem", "difficulty", "hint", "solution_steps", "full_solution"}, ...]
    """
    prompt = f"""以下の数学の問題から、難易度が異なる 3 つの類題を生成してください。

【元の問題】
{problem_text}

【生成要件】
1. 「基本」「標準」「応用」の3段階で難易度を設定
2. 中学2年生の莉亜さん向けに、教科書 {textbook_reference} の解き方に準じること
3. 各問題に対してステップバイステップの解法を含めること
4. 各問題に簡潔なヒントを含めること

【出力形式】
以下の JSON 配列で返してください（説明は不要）：
[
  {{
    "id": "gen_001",
    "problem": "問題文",
    "difficulty": "基本",
    "hint": "ヒント（1-2文）",
    "solution_steps": ["ステップ1", "ステップ2"],
    "full_solution": "完全な解答"
  }},
  {{
    "id": "gen_002",
    "problem": "問題文",
    "difficulty": "標準",
    "hint": "ヒント（1-2文）",
    "solution_steps": ["ステップ1", "ステップ2"],
    "full_solution": "完全な解答"
  }},
  {{
    "id": "gen_003",
    "problem": "問題文",
    "difficulty": "応用",
    "hint": "ヒント（1-2文）",
    "solution_steps": ["ステップ1", "ステップ2"],
    "full_solution": "完全な解答"
  }}
]"""

    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        problems = _extract_json(message.content[0].text)
        return problems if isinstance(problems, list) else []
    except Exception as e:
        print(f"Error generating problems: {e}")
        return []


def generate_explanation(problem_text: str, user_answer: str = None, is_correct: bool = None) -> str:
    """莉亜さん向けの詳しい解説を生成"""
    if user_answer and is_correct is False:
        prompt = f"""莉亜さんが以下の数学の問題を間違えました。
どこが間違っていたか、どうすれば正解できるかを、中学2年生に分かるように丁寧に説明してください。

【問題】
{problem_text}

【莉亜さんの回答】
{user_answer}

【説明のポイント】
- ステップバイステップで分かりやすく
- 莉亜さんの間違いがどこにあったかを具体的に指摘
- なぜそこが間違ったのかを丁寧に説明
- 正しい解法を示す
- 最後に「次からはこうするといいよ」とアドバイス

解説のみを返してください。"""
    else:
        prompt = f"""以下の数学の問題について、中学2年生の莉亜さんに向けた詳しい解説を書いてください。

【問題】
{problem_text}

【解説のポイント】
- 最初に「この問題のポイント」を1-2文で
- ステップバイステップで解き方を説明
- 各ステップで「なぜこうするのか」という理由を含める
- 最後に「類似の問題に出会ったときのコツ」を教える

解説のみを返してください。"""

    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def save_generated_problems(problems: list, chapter: str, subject: str = "math") -> str:
    """生成した問題を JSON ファイルで保存（ローカル）"""
    date_str = _now_jst().strftime("%Y-%m-%d")
    filename = f"data/study_agent/generated_problems/{subject}_{date_str}.json"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": _now_jst().isoformat(),
        "chapter": chapter,
        "subject": subject,
        "problems": problems
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename
