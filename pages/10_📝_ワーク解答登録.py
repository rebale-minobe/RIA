"""
ワーク解答登録ページ
- スクショをアップロード → Claude Vision で JSON 抽出
- プレビュー＆編集後、data/{subject}_{genre}_workbook_answers.json に追記
- GitHub push で本番反映
"""
import streamlit as st
import json
import base64
import io
from pathlib import Path
from PIL import Image
from anthropic import Anthropic

from modules.gh import gh_put, gh_get_text

st.set_page_config(page_title="ワーク解答登録 - RIA", page_icon="📝", layout="wide")

# ===== 教科 × ジャンル =====
SUBJECTS = {
    "social": {"name": "社会", "emoji": "🗺️", "genres": {
        "history": "歴史", "geography": "地理", "civics": "公民",
    }},
    "japanese": {"name": "国語", "emoji": "📘", "genres": {
        "reading": "読解", "classic": "古文・漢文",
        "kanji": "漢字・語彙", "grammar": "文法",
    }},
    "math": {"name": "数学", "emoji": "📐", "genres": {"general": "数学"}},
    "science": {"name": "理科", "emoji": "🔬", "genres": {
        "field1": "第1分野", "field2": "第2分野",
    }},
    "english": {"name": "英語", "emoji": "🌐", "genres": {"general": "英語"}},
}

DATA_DIR = Path(__file__).parent.parent / "data"

# ===== 抽出プロンプト =====
EXTRACTION_PROMPT = """\
あなたは中学校のワーク（問題集）の解答ページを構造化JSONに変換するアシスタントです。

# 出力形式（必ずこのスキーマ通りのJSONを返す）

```json
{
  "page_number": 2,
  "question_pages_ref": "本誌 P.2・3",
  "chapter_number": "第4章",
  "chapter_title": "武家政権の展開と世界の動き",
  "lesson_title": "大航海によって結びつく世界",
  "sections": [
    {
      "code": "地図",
      "name": "地図でおさえよう",
      "textbook_ref": "本誌 P.54",
      "subtitle": null,
      "groups": [
        {
          "label": null,
          "answers": [
            {"q": "①", "a": "イ", "note": null, "context": null}
          ]
        }
      ]
    },
    {
      "code": "A",
      "name": "教科書で確認",
      "textbook_ref": "本誌 P.54",
      "subtitle": null,
      "groups": [
        {
          "label": "[1]",
          "answers": [
            {"q": "①", "a": "ローマ教皇[法王]", "note": null, "context": null}
          ]
        }
      ]
    }
  ]
}
```

# 抽出ルール

## page_number
- ページの隅にある小さな番号（解答ページの通し番号、例: 1, 2, 3...）

## question_pages_ref
- ページ右上の「本誌 P.X」や「本誌 P.X・Y」表記をそのまま文字列で

## chapter_number / chapter_title
- ページ最上部の「第4章」「武家政権の展開と世界の動き」など
- 章情報がない要約ページなどは両方 null

## lesson_title
- 大きく書かれた見出しタイトル（例: 「大航海によって結びつく世界」）

## sections[]
セクション = ページ内の青や緑のラベル付き枠ごと。よくあるもの:
- code="地図", name="地図でおさえよう"
- code="A",  name="教科書で確認"
- code="B",  name="力をつけよう"
- code="B+", name="資料の活用"
- code="C",  name="日本と世界の流れをまとめよう!" など
- 各セクション内の「本誌 P.X」表記は textmark_ref ではなく **textbook_ref** に入れる
- subtitle: 「①〜⑪にあてはまる語句」のような補足見出しがあれば

## groups[]
- セクション内の [1] [2] [3] 区切り。区切りが無い場合は label=null で1グループ
- 時系列ページで「① 長篠の戦い」「② 刀狩令」のような資料ラベルがある場合、それを label に

## answers[]
- q: 質問の識別子。①〜⑯、(1)(2)(3)(4)、(2)①、(2) a、(2) X など、画像通りの記号を保持
- a: 解答テキスト。「(例)…」の表記、「ローマ教皇[法王]」の角括弧表記もそのまま保持
- note: 「※漢字1字でなければ不可」「※順番が逆でも可」「理由」「目的」など答えに付随する注記
- context: 時系列まとめページなどで「いつ・どんな出来事」の手がかりがある場合に保持。通常は null

# 重要

- JSONのみを返す。説明文や前置きは一切不要
- ```json コードフェンスで囲んで返す
- 全てのフィールドを必ず含める（該当しない場合は null）
- 答えに含まれる「=」「・」「[]」などの記号は画像通り正確に保持
- 「(例)」プレフィックスの記述問題は a の先頭に「(例)」を残す
"""


def resize_image_for_api(image_bytes: bytes, max_dim: int = 1568) -> tuple[bytes, str]:
    """Anthropic API向けに画像をリサイズ"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue(), "image/jpeg"


def extract_page_from_image(image_bytes: bytes, subject_name: str, genre_name: str) -> dict:
    """Claude Vision でスクショから1ページ分のJSON抽出"""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が Secrets に登録されていません")

    resized, mime = resize_image_for_api(image_bytes)
    b64 = base64.b64encode(resized).decode("utf-8")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=EXTRACTION_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": b64},
                },
                {
                    "type": "text",
                    "text": f"{subject_name}（{genre_name}）のワーク解答ページです。スキーマ通りのJSONに変換してください。"
                },
            ],
        }],
    )

    text = response.content[0].text.strip()
    # コードフェンス除去
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def get_filename(subject_key: str, genre_key: str) -> str:
    return f"{subject_key}_{genre_key}_workbook_answers.json"


def load_existing(subject_key: str, genre_key: str) -> dict | None:
    """既存のワーク解答JSONを読み込み（無ければNone）"""
    filename = get_filename(subject_key, genre_key)

    # ローカル優先
    local_path = DATA_DIR / filename
    if local_path.exists():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # GitHub フォールバック
    try:
        text = gh_get_text(f"data/{filename}")
        if text:
            return json.loads(text)
    except Exception:
        pass

    return None


def merge_pages(existing: dict, new_pages: list[dict]) -> dict:
    """既存pagesに新規pagesを upsert（page_numberで重複チェック）"""
    by_num = {p["page_number"]: p for p in existing.get("pages", [])}
    for np in new_pages:
        by_num[np["page_number"]] = np  # 上書き
    existing["pages"] = sorted(by_num.values(), key=lambda p: p["page_number"])
    return existing


# ===== UI =====
st.title("📝 ワーク解答登録")
st.caption("ワーク解答ページのスクショから自動でJSON抽出・登録します")

# ─── Step 1: 教科・ジャンル選択 ───
st.markdown("### 1️⃣ 教科とジャンルを選択")
col1, col2 = st.columns(2)
with col1:
    subject_labels = [f"{v['emoji']} {v['name']}" for v in SUBJECTS.values()]
    subject_keys = list(SUBJECTS.keys())
    sel_subject_label = st.selectbox("教科", subject_labels, key="reg_subject")
    subject_key = subject_keys[subject_labels.index(sel_subject_label)]
    sinfo = SUBJECTS[subject_key]

with col2:
    genre_labels = list(sinfo["genres"].values())
    genre_keys = list(sinfo["genres"].keys())
    sel_genre_label = st.selectbox("ジャンル", genre_labels, key="reg_genre")
    genre_key = genre_keys[genre_labels.index(sel_genre_label)]

# 既存データチェック
existing = load_existing(subject_key, genre_key)
if existing:
    existing_pages = existing.get("pages", [])
    st.info(f"📚 既存データ: **{existing.get('workbook_title', '')}** "
            f"／ 登録済 {len(existing_pages)} ページ "
            f"（P.{', P.'.join(str(p['page_number']) for p in sorted(existing_pages, key=lambda x: x['page_number']))}）")
else:
    st.warning("🆕 このジャンルは新規登録です。ワーク名を入力してください。")
    new_workbook_title = st.text_input(
        "ワーク名（例: 歴史2・3年 帝国書院 まとめのワーク）",
        key="new_wb_title"
    )

st.markdown("---")

# ─── Step 2: スクショアップロード ───
st.markdown("### 2️⃣ ワーク解答ページのスクショをアップロード")
uploaded_files = st.file_uploader(
    "1ページ = 1ファイル。複数枚OK（順不同で可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="reg_uploader",
)

if uploaded_files:
    st.caption(f"📷 {len(uploaded_files)}枚アップロード")
    with st.expander("プレビュー", expanded=False):
        cols = st.columns(min(len(uploaded_files), 3))
        for i, f in enumerate(uploaded_files):
            with cols[i % 3]:
                st.image(f, caption=f.name, use_column_width=True)

st.markdown("---")

# ─── Step 3: JSON抽出 ───
st.markdown("### 3️⃣ JSON抽出")

if st.button("🔍 抽出する", type="primary", use_container_width=True,
             disabled=not uploaded_files):
    if not uploaded_files:
        st.error("画像をアップロードしてください")
        st.stop()

    extracted = []
    errors = []
    progress = st.progress(0, text="抽出中...")

    for i, f in enumerate(uploaded_files):
        progress.progress((i) / len(uploaded_files), text=f"抽出中... {f.name}")
        try:
            f.seek(0)
            image_bytes = f.read()
            page_data = extract_page_from_image(
                image_bytes,
                sinfo["name"],
                sinfo["genres"][genre_key]
            )
            extracted.append(page_data)
        except Exception as e:
            errors.append(f"{f.name}: {e}")

    progress.progress(1.0, text="完了")
    progress.empty()

    if errors:
        for err in errors:
            st.error(f"❌ {err}")
    if extracted:
        st.success(f"✅ {len(extracted)}ページ抽出成功！")
        st.session_state["reg_extracted"] = extracted

# ─── Step 4: プレビュー＆編集 ───
if "reg_extracted" in st.session_state and st.session_state["reg_extracted"]:
    st.markdown("---")
    st.markdown("### 4️⃣ プレビュー＆編集")
    st.caption("抽出されたJSONを確認。間違いがあれば直接編集してください。")

    json_text = st.text_area(
        "JSON（編集可）",
        value=json.dumps(
            {"pages": st.session_state["reg_extracted"]},
            ensure_ascii=False, indent=2
        ),
        height=500,
        key="reg_json_edit",
    )

    # 視覚プレビュー
    with st.expander("📋 視覚プレビュー", expanded=True):
        try:
            preview_data = json.loads(json_text)
            for page in preview_data["pages"]:
                st.markdown(f"#### 📄 P.{page['page_number']} — {page.get('lesson_title','')}")
                st.caption(f"参照: {page.get('question_pages_ref','')}")
                for section in page.get("sections", []):
                    sec_head = f"**{section['code']}** {section['name']}"
                    if section.get("textbook_ref"):
                        sec_head += f"　— {section['textbook_ref']}"
                    st.markdown(sec_head)
                    for group in section.get("groups", []):
                        if group.get("label"):
                            st.markdown(f"　**{group['label']}**")
                        for ans in group.get("answers", []):
                            note = f" *※{ans['note']}*" if ans.get("note") else ""
                            st.markdown(f"　`{ans['q']}` {ans['a']}{note}")
                st.markdown("")
        except json.JSONDecodeError as e:
            st.error(f"JSON構文エラー: {e}")

    # ─── Step 5: 保存 ───
    st.markdown("---")
    st.markdown("### 5️⃣ 保存して登録")

    if st.button("💾 保存する（GitHub push）", type="primary", use_container_width=True):
        try:
            new_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            st.error(f"JSON構文エラー: {e}")
            st.stop()

        new_pages = new_data.get("pages", [])
        if not new_pages:
            st.error("保存するページがありません")
            st.stop()

        # 既存とマージ
        if existing:
            merged = merge_pages(existing, new_pages)
        else:
            wb_title = st.session_state.get("new_wb_title", "")
            if not wb_title:
                st.error("新規登録の場合はワーク名を入力してください")
                st.stop()
            merged = {
                "subject": subject_key,
                "genre": genre_key,
                "workbook_title": wb_title,
                "pages": sorted(new_pages, key=lambda p: p["page_number"]),
            }

        # GitHub push
        filename = get_filename(subject_key, genre_key)
        path = f"data/{filename}"
        content = json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8")

        try:
            with st.spinner("GitHub に保存中..."):
                gh_put(
                    path, content,
                    f"Add/update workbook answers: {subject_key}/{genre_key} ({len(new_pages)} pages)"
                )
            st.success(f"🎉 保存完了！ 計 {len(merged['pages'])} ページ登録済み")
            st.balloons()
            # クリア
            del st.session_state["reg_extracted"]
            st.caption("Streamlit Cloud が再デプロイされたら、教科ページの「📝 ワーク解答」から確認できます。")
        except Exception as e:
            st.error(f"❌ 保存失敗: {e}")
            st.exception(e)

# ===== サイドバー =====
with st.sidebar:
    st.markdown("### 📖 使い方")
    st.markdown("""
1. 教科・ジャンルを選択
2. ワーク解答ページのスクショをアップロード（1ページ = 1枚）
3. **抽出する** ボタンで Claude が自動でJSON化
4. プレビューを確認、必要なら修正
5. **保存する** ボタンで GitHub に登録
6. 教科ページの「📝 ワーク解答」で確認！
    """)
    st.markdown("---")
    st.markdown("### ⚙️ 必要な設定")
    st.markdown("""
- `ANTHROPIC_API_KEY` (Secrets)
- `GITHUB_PAT` (Secrets / `modules/gh.py` で使用)
    """)
