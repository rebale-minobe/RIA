"""
RIA 教科書登録システム（ジャンル対応版） + GitHub自動push
教科 → ジャンル → 教科書（表紙・出版社・目次）の3階層
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path

# GitHub API helper（modules/gh.py）
from modules.gh import gh_put

# ===== ページ設定 =====
st.set_page_config(page_title="📕 教科書登録", layout="wide")

# ===== スタイル =====
st.markdown("""
<style>
    .cover-placeholder {
        background: linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%);
        height: 160px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #888;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ===== 教科 × ジャンル定義 =====

SUBJECTS = {
    "social": {
        "name": "社会", "emoji": "🗺️",
        "genres": {
            "history": {"name": "歴史", "emoji": "📜"},
            "geography": {"name": "地理", "emoji": "🌏"},
            "civics": {"name": "公民", "emoji": "⚖️"},
        }
    },
    "japanese": {
        "name": "国語", "emoji": "📘",
        "genres": {
            "jp2": {"name": "国語2", "emoji": "📘"},
        }
    },
    "math": {
        "name": "数学", "emoji": "📐",
        "genres": {
            "math1": {"name": "数学1", "emoji": "📐"},
            "math2": {"name": "数学2", "emoji": "📐"},
        }
    },
    "science": {
        "name": "理科", "emoji": "🔬",
        "genres": {
            "field1": {"name": "サイエンス1", "emoji": "🌱"},
            "field2": {"name": "サイエンス2", "emoji": "🌱"},
        }
    },
    "english": {
        "name": "英語", "emoji": "🌐",
        "genres": {
            "eng2": {"name": "英語2", "emoji": "🌐"},
        }
    },
}

DATA_DIR = Path(__file__).parent.parent / "data"
COVERS_DIR = DATA_DIR / "textbook_covers"


def get_textbook_filename(subject_key: str, genre_key: str) -> str:
    return f"{subject_key}_{genre_key}_textbook.json"


def load_textbook(subject_key: str, genre_key: str):
    filename = get_textbook_filename(subject_key, genre_key)
    local_path = DATA_DIR / filename
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def update_textbook_metadata(subject_key, genre_key, publisher, cover_filename, textbook_name):
    filename = get_textbook_filename(subject_key, genre_key)
    local_path = DATA_DIR / filename

    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"textbook": {"chapters": []}}

    if "textbook" not in data:
        data["textbook"] = {"chapters": []}

    if textbook_name:
        data["textbook"]["name"] = textbook_name
    if publisher:
        data["textbook"]["publisher"] = publisher
    if cover_filename:
        data["textbook"]["cover_image"] = f"textbook_covers/{cover_filename}"

    data["textbook"]["subject"] = subject_key
    data["textbook"]["genre"] = genre_key
    data["textbook"]["registered_at"] = datetime.now().isoformat()

    with open(local_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True




_GENRE_SHEET_MAP = {
    "history": "歴史", "geography": "地理", "civics": "公民",
    "reading": "読解", "classic": "古文漢文",
    "kanji": "漢字語彙", "grammar": "文法",
    "field1": "サイエンス1", "field2": "サイエンス2",
    "jp2": "国語2",
    "math1": "数学1",
    "math2": "数学2",
    "eng2": "英語2",
    "general": "一般",
}

def has_toc_in_excel(subject_key: str, genre_key: str) -> bool:
    """Excelファイルに目次シートが存在するか確認"""
    try:
        import openpyxl
        excel_path = DATA_DIR / f"{subject_key}_data.xlsx"
        sheet_name = f"目次_{_GENRE_SHEET_MAP.get(genre_key, genre_key)}"
        if excel_path.exists():
            wb = openpyxl.load_workbook(excel_path, read_only=True)
            result = sheet_name in wb.sheetnames
            wb.close()
            return result
    except Exception:
        pass
    return False

def save_cover_image(subject_key, genre_key, uploaded_file):
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    ext = uploaded_file.name.split('.')[-1].lower()
    cover_filename = f"{subject_key}_{genre_key}.{ext}"
    cover_path = COVERS_DIR / cover_filename
    with open(cover_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return cover_filename


# ===== メイン UI =====

st.title("📕 教科書登録")
st.write("教科 → ジャンル → 教科書情報(表紙・出版社)を登録します。")

tab_register, tab_view = st.tabs(["📝 教科書を登録", "📚 登録済み教科書"])

# ===== タブ 1: 登録 =====

with tab_register:
    st.markdown("### 教科書情報を登録")

    col_subject, col_genre = st.columns(2)

    with col_subject:
        subject_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
        selected_subject_label = st.selectbox("📚 教科を選択", list(subject_options.keys()))
        selected_subject = subject_options[selected_subject_label]

    with col_genre:
        genres = SUBJECTS[selected_subject]["genres"]
        genre_options = {f"{v['emoji']} {v['name']}": k for k, v in genres.items()}
        selected_genre_label = st.selectbox("🏷️ ジャンルを選択", list(genre_options.keys()))
        selected_genre = genre_options[selected_genre_label]

    existing_data = load_textbook(selected_subject, selected_genre)
    has_toc = (existing_data and existing_data.get("textbook", {}).get("chapters")) or has_toc_in_excel(selected_subject, selected_genre)

    subject_name = SUBJECTS[selected_subject]["name"]
    genre_name = genres[selected_genre]["name"]

    if has_toc:
        chapters_count = len(existing_data["textbook"]["chapters"]) if existing_data and existing_data.get("textbook", {}).get("chapters") else "Excel"
        st.success(f"✅ {subject_name}({genre_name})の目次は登録済み（{chapters_count}）")
    else:
        st.warning(f"⚠️ {subject_name}({genre_name})の目次はまだ登録されていません")

    st.markdown("---")

    current_name = ""
    current_publisher = ""
    if existing_data:
        current_name = existing_data.get("textbook", {}).get("name", "")
        current_publisher = existing_data.get("textbook", {}).get("publisher", "")
        if current_publisher == "未設定":
            current_publisher = ""

    textbook_name = st.text_input(
        "📕 教科書名",
        value=current_name,
        placeholder="例: 中学生の歴史 日本の歩みと世界の動き"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📖 出版社")
        publisher = st.text_input(
            "出版社名",
            value=current_publisher,
            placeholder="例: 帝国書院、東京書籍"
        )

    with col2:
        st.markdown("#### 🖼️ 表紙画像")
        uploaded_cover = st.file_uploader(
            "表紙画像をアップロード",
            type=["jpg", "jpeg", "png"],
            key="cover_upload"
        )
        if uploaded_cover:
            st.image(uploaded_cover, width=140, caption="プレビュー")

    st.markdown("---")

    if st.button("✅ 教科書情報を登録", type="primary", use_container_width=True):
        # 1) ローカル保存(Streamlit Cloud側)
        cover_filename = ""
        if uploaded_cover:
            cover_filename = save_cover_image(selected_subject, selected_genre, uploaded_cover)
            st.success(f"🖼️ 表紙画像を保存: {cover_filename}")

        update_textbook_metadata(selected_subject, selected_genre, publisher, cover_filename, textbook_name)
        st.success(f"🎉 {subject_name}({genre_name})の教科書情報をローカル保存しました")

        # 2) GitHub に自動 push
        try:
            # 表紙画像を先に push (JSONの cover_image が指す先を作っておく)
            if cover_filename:
                gh_put(
                    f"data/textbook_covers/{cover_filename}",
                    (COVERS_DIR / cover_filename).read_bytes(),
                    f"Upload cover: {subject_name}({genre_name})"
                )
            # 教科書JSONを push
            json_filename = get_textbook_filename(selected_subject, selected_genre)
            gh_put(
                f"data/{json_filename}",
                (DATA_DIR / json_filename).read_bytes(),
                f"Register textbook: {subject_name}({genre_name})"
            )
            st.success("☁️ GitHub に反映しました(30秒〜1分で本番に自動デプロイされます)")
        except Exception as e:
            st.error(f"GitHub反映エラー: {e}")
            st.info("ローカル保存は完了しています。手動で push してください。")

# ===== タブ 2: 閲覧 =====

with tab_view:
    st.markdown("### 登録済み教科書一覧")

    for subject_key, subject_info in SUBJECTS.items():
        st.markdown(f"#### {subject_info['emoji']} {subject_info['name']}")

        genres = subject_info["genres"]
        cols = st.columns(len(genres))

        for i, (genre_key, genre_info) in enumerate(genres.items()):
            with cols[i]:
                data = load_textbook(subject_key, genre_key)
                st.markdown(f"**{genre_info['emoji']} {genre_info['name']}**")

                if data and data.get("textbook"):
                    tb = data["textbook"]
                    cover = tb.get("cover_image", "")
                    cover_path = DATA_DIR / cover if cover else None

                    if cover_path and cover_path.exists():
                        st.image(str(cover_path), use_container_width=True)
                    else:
                        st.markdown('<div class="cover-placeholder">表紙未登録</div>', unsafe_allow_html=True)

                    st.caption(f"📖 {tb.get('publisher', '未登録')}")
                    chapters = len(tb.get("chapters", []))
                    st.caption(f"📑 {chapters}章" if chapters else "目次未登録")
                else:
                    st.markdown('<div class="cover-placeholder">未登録</div>', unsafe_allow_html=True)
        st.markdown("")

    st.markdown("---")
    st.markdown("### 📑 目次を見る")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        v_subject_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
        v_subject_label = st.selectbox("教科", list(v_subject_options.keys()), key="v_subject")
        v_subject = v_subject_options[v_subject_label]
    with col_v2:
        v_genres = SUBJECTS[v_subject]["genres"]
        v_genre_options = {f"{v['emoji']} {v['name']}": k for k, v in v_genres.items()}
        v_genre_label = st.selectbox("ジャンル", list(v_genre_options.keys()), key="v_genre")
        v_genre = v_genre_options[v_genre_label]

    v_data = load_textbook(v_subject, v_genre)

    if v_data and v_data.get("textbook", {}).get("chapters"):
        for chapter in v_data["textbook"]["chapters"]:
            ch_title = f"{chapter.get('chapter_number', '')} {chapter['title']}"
            with st.expander(f"📖 {ch_title}"):
                for section in chapter.get("sections", []):
                    st.markdown(f"**{section['title']}**")
                    for sub in section.get("subsections", []):
                        st.markdown(f"　• {sub['title']} (p.{sub['page']})")
    else:
        st.info("この教科書の目次はまだ登録されていません")

# ===== サイドバー =====
st.sidebar.markdown("### 📕 3階層構造")
st.sidebar.markdown("""
**教科 → ジャンル → 教科書**

例:
- 社会 → 歴史 → 中学生の歴史
- 社会 → 地理 → 中学社会 地理的分野
- 国語 → 古文 → (後で)

ジャンルごとに目次・進捗を
別々に管理できます。
""")

st.markdown("---")
st.caption("🌟 RIA | 教科書登録システム v2.1(GitHub自動push)")
