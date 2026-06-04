"""
ワーク解答登録ページ (v0.2: 表紙画像対応)
- スクショ + 表紙画像 をアップロード → Claude Vision で JSON 抽出
- data/{subject}_{genre}_workbook_answers.json に追記、表紙は workbook_covers/ へ
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

- **page_number**: ページ隅の小さな通し番号
- **question_pages_ref**: ページ右上「本誌 P.X」「本誌 P.X・Y」をそのまま文字列で
- **chapter_number / chapter_title**: 上部の章情報。無ければ両方 null
- **lesson_title**: 大きな見出しタイトル
- **sections**: ページ内のラベル付き枠ごと。code は「地図」「A」「B」「B+」「C」「資料」など / name は「教科書で確認」「力をつけよう」「資料の活用」など
- **textbook_ref**: セクション内の「本誌 P.X」表記
- **groups.label**: [1] [2] [3]。区切りが無い場合は null
- **answers**:
  - q: 質問識別子 (①〜⑯、(1)(2)(3)(4)、(2)①、(2) a など、画像通り)
  - a: 解答。「(例)」「[法王]」表記もそのまま保持
  - note: 「※漢字1字でなければ不可」「順番が逆でも可」「理由」「目的」など
  - context: 時系列まとめページなどで「いつ・どんな出来事」の手がかり

# 重要

- JSONのみを返す。説明文や前置きは一切不要
- ```json コードフェンスで囲んで返す
- 全フィールド必須（該当しない場合は null）
- 答えの記号「=」「・」「[]」は画像通り保持
- 記述問題の「(例)」は a の先頭に残す
"""


def resize_image_for_api(image_bytes: bytes, max_dim: int = 1568) -> tuple[bytes, str]:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue(), "image/jpeg"


def process_cover_image(image_bytes: bytes, max_dim: int = 800) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


def extract_page_from_image(image_bytes: bytes, subject_name: str, genre_name: str) -> dict:
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
                {"type": "image",
                 "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text",
                 "text": f"{subject_name}（{genre_name}）のワーク解答ページです。スキーマ通りのJSONに変換してください。"},
            ],
        }],
    )

    text = response.content[0].text.strip()
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


def get_cover_filename(subject_key: str, genre_key: str) -> str:
    return f"workbook_covers/{subject_key}_{genre_key}.jpg"


def load_existing(subject_key: str, genre_key: str) -> dict | None:
    filename = get_filename(subject_key, genre_key)
    local_path = DATA_DIR / filename
    if local_path.exists():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    try:
        text = gh_get_text(f"data/{filename}")
        if text:
            return json.loads(text)
    except Exception:
        pass
    return None


def merge_pages(existing: dict, new_pages: list[dict]) -> dict:
    by_num = {p["page_number"]: p for p in existing.get("pages", [])}
    for np in new_pages:
        by_num[np["page_number"]] = np
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

existing = load_existing(subject_key, genre_key)
is_new = existing is None

if existing:
    pages_list = existing.get("pages", [])
    page_nums_str = ', '.join(str(p['page_number']) for p in sorted(pages_list, key=lambda x: x['page_number']))
    cover_status = "✅ 表紙登録済" if existing.get("cover_image") else "⚠️ 表紙未登録"
    st.info(f"📚 既存データ: **{existing.get('workbook_title', '')}** "
            f"／ 登録済 {len(pages_list)} ページ（P.{page_nums_str}）／ {cover_status}")
else:
    st.warning("🆕 このジャンルは新規登録です")

# ─── Step 1b: ワーク情報 ───
new_workbook_title = ""
cover_file = None
if is_new:
    st.markdown("#### 📚 ワーク情報")
    new_workbook_title = st.text_input(
        "ワーク名（例: 歴史2・3年 帝国書院 まとめのワーク）",
        key="new_wb_title"
    )
    cover_file = st.file_uploader(
        "🖼️ ワーク表紙画像（任意・JPEG/PNG）",
        type=["jpg", "jpeg", "png"],
        key="new_wb_cover",
    )
elif not existing.get("cover_image"):
    with st.expander("🖼️ 表紙画像を追加（未登録）", expanded=False):
        add_cover_file = st.file_uploader(
            "表紙画像をアップロード",
            type=["jpg", "jpeg", "png"],
            key="add_cover_file",
        )
        if add_cover_file and st.button("📷 表紙だけ保存する", key="save_cover_only"):
            try:
                cover_bytes = process_cover_image(add_cover_file.read())
                cover_path = get_cover_filename(subject_key, genre_key)
                with st.spinner("表紙を保存中..."):
                    gh_put(f"data/{cover_path}", cover_bytes,
                           f"Add workbook cover: {subject_key}/{genre_key}")
                    existing["cover_image"] = cover_path
                    full_path = f"data/{get_filename(subject_key, genre_key)}"
                    gh_put(full_path,
                           json.dumps(existing, ensure_ascii=False, indent=2).encode("utf-8"),
                           f"Link workbook cover: {subject_key}/{genre_key}")
                st.success("🎉 表紙を登録しました！")
                st.rerun()
            except Exception as e:
                st.error(f"表紙保存失敗: {e}")

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
        progress.progress(i / len(uploaded_files), text=f"抽出中... {f.name}")
        try:
            f.seek(0)
            image_bytes = f.read()
            page_data = extract_page_from_image(
                image_bytes, sinfo["name"], sinfo["genres"][genre_key]
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

        # 表紙画像保存
        cover_path_value = None
        if cover_file:
            try:
                cover_bytes = process_cover_image(cover_file.read())
                cover_path = get_cover_filename(subject_key, genre_key)
                with st.spinner("表紙を保存中..."):
                    gh_put(
                        f"data/{cover_path}",
                        cover_bytes,
                        f"Add workbook cover: {subject_key}/{genre_key}"
                    )
                cover_path_value = cover_path
            except Exception as e:
                st.warning(f"表紙保存エラー: {e}")

        # マージ
        if existing:
            merged = merge_pages(existing, new_pages)
            if cover_path_value:
                merged["cover_image"] = cover_path_value
        else:
            if not new_workbook_title:
                st.error("新規登録の場合はワーク名を入力してください")
                st.stop()
            merged = {
                "subject": subject_key,
                "genre": genre_key,
                "workbook_title": new_workbook_title,
                "pages": sorted(new_pages, key=lambda p: p["page_number"]),
            }
            if cover_path_value:
                merged["cover_image"] = cover_path_value

        # GitHub push
        filename = get_filename(subject_key, genre_key)
        path = f"data/{filename}"
        content = json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8")

        try:
            with st.spinner("GitHub に保存中..."):
                gh_put(path, content,
                       f"Add/update workbook answers: {subject_key}/{genre_key} ({len(new_pages)} pages)")
            st.success(f"🎉 保存完了！ 計 {len(merged['pages'])} ページ登録済み")
            st.balloons()
            del st.session_state["reg_extracted"]
            st.caption("Streamlit Cloud が再デプロイされたら、TOPの 📚 教科書/ワーク から確認できます。")
        except Exception as e:
            st.error(f"❌ 保存失敗: {e}")
            st.exception(e)

# ===== サイドバー =====
with st.sidebar:
    st.markdown("### 📖 使い方")
    st.markdown("""
1. 教科・ジャンルを選択
2. 新規ならワーク名＆表紙画像
3. ワーク解答ページのスクショをアップロード（1ページ = 1枚）
4. **抽出する** で Claude が自動でJSON化
5. プレビュー確認・修正
6. **保存する** で GitHub に登録
7. TOPの 📚 教科書/ワーク でワーク選択 → 解答ページ表示
    """)
