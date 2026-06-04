"""
RIA 教科書登録システム
教科書の表紙画像 + 出版社情報を登録
登録した教科書を選択 → 目次表示 → 章を押すとポイント
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path

# ===== ページ設定 =====
st.set_page_config(page_title="📕 教科書登録", layout="wide")

# ===== スタイル =====
st.markdown("""
<style>
    .textbook-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        text-align: center;
        border: 1px solid #f0f0f0;
    }
    .cover-placeholder {
        background: linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%);
        height: 200px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #888;
        font-size: 14px;
    }
    .chapter-item {
        background: #f0f4ff;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #4a90e2;
        margin: 8px 0;
        cursor: pointer;
    }
    .section-title {
        font-size: 22px;
        font-weight: 700;
        margin: 20px 0 12px 0;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# ===== 教科設定 =====

SUBJECTS = {
    "social": {"name": "社会", "emoji": "🗺️", "textbook_file": "social_textbook.json"},
    "japanese": {"name": "国語", "emoji": "📘", "textbook_file": "japanese_textbook.json"},
    "math": {"name": "数学", "emoji": "📐", "textbook_file": "math_textbook.json"},
    "science": {"name": "理科", "emoji": "🔬", "textbook_file": "science_textbook.json"},
    "english": {"name": "英語", "emoji": "🌐", "textbook_file": "english_textbook.json"},
}

DATA_DIR = Path(__file__).parent.parent / "data"
COVERS_DIR = DATA_DIR / "textbook_covers"

# ===== データ操作 =====

def load_textbook(subject_key: str):
    """教科書データを読み込む"""
    textbook_file = SUBJECTS[subject_key]["textbook_file"]
    local_path = DATA_DIR / textbook_file
    
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def update_textbook_metadata(subject_key: str, publisher: str, cover_filename: str):
    """教科書のメタ情報（出版社・表紙）を更新"""
    textbook_file = SUBJECTS[subject_key]["textbook_file"]
    local_path = DATA_DIR / textbook_file
    
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"textbook": {"chapters": []}}
    
    # メタ情報を更新
    if publisher:
        data["textbook"]["publisher"] = publisher
    if cover_filename:
        data["textbook"]["cover_image"] = f"textbook_covers/{cover_filename}"
    
    data["textbook"]["registered_at"] = datetime.now().isoformat()
    
    with open(local_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return True

def save_cover_image(subject_key: str, uploaded_file):
    """表紙画像を保存"""
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 拡張子を取得
    ext = uploaded_file.name.split('.')[-1].lower()
    cover_filename = f"{subject_key}.{ext}"
    cover_path = COVERS_DIR / cover_filename
    
    with open(cover_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return cover_filename

# ===== メイン UI =====

st.title("📕 教科書登録")
st.write("教科書の表紙と出版社を登録します。登録後、目次から学習できます。")

# タブ: 登録 / 閲覧
tab_register, tab_view = st.tabs(["📝 教科書を登録", "📚 登録済み教科書"])

# ===== タブ 1: 登録 =====

with tab_register:
    st.markdown("### 教科書情報を登録")
    
    # 教科選択
    subject_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
    selected_label = st.selectbox("教科を選択", list(subject_options.keys()))
    selected_subject = subject_options[selected_label]
    
    # 既存データの確認
    existing_data = load_textbook(selected_subject)
    has_toc = existing_data and existing_data.get("textbook", {}).get("chapters")
    
    if has_toc:
        st.success(f"✅ {SUBJECTS[selected_subject]['name']}の目次は登録済みです（{len(existing_data['textbook']['chapters'])}章）")
    else:
        st.warning(f"⚠️ {SUBJECTS[selected_subject]['name']}の目次はまだ登録されていません")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📖 出版社")
        current_publisher = ""
        if existing_data:
            current_publisher = existing_data.get("textbook", {}).get("publisher", "")
            if current_publisher == "未設定":
                current_publisher = ""
        
        publisher = st.text_input(
            "出版社名",
            value=current_publisher,
            placeholder="例: 東京書籍、帝国書院、教育出版"
        )
    
    with col2:
        st.markdown("#### 🖼️ 表紙画像")
        uploaded_cover = st.file_uploader(
            "表紙画像をアップロード",
            type=["jpg", "jpeg", "png"],
            key="cover_upload"
        )
        
        if uploaded_cover:
            st.image(uploaded_cover, width=150, caption="プレビュー")
    
    st.markdown("---")
    
    # 登録ボタン
    if st.button("✅ 教科書情報を登録", type="primary", use_container_width=True):
        cover_filename = ""
        
        if uploaded_cover:
            cover_filename = save_cover_image(selected_subject, uploaded_cover)
            st.success(f"🖼️ 表紙画像を保存しました: {cover_filename}")
        
        update_textbook_metadata(selected_subject, publisher, cover_filename)
        
        st.success(f"🎉 {SUBJECTS[selected_subject]['name']}の教科書情報を登録しました！")
        st.info("⚠️ 表紙画像を本番反映するには、data/textbook_covers/ を GitHub に push してください")

# ===== タブ 2: 閲覧 =====

with tab_view:
    st.markdown("### 登録済み教科書")
    
    # 全教科の登録状況を表示
    cols = st.columns(5)
    
    for i, (subject_key, subject_info) in enumerate(SUBJECTS.items()):
        with cols[i]:
            data = load_textbook(subject_key)
            
            if data and data.get("textbook"):
                tb = data["textbook"]
                publisher = tb.get("publisher", "未登録")
                cover = tb.get("cover_image", "")
                chapters = len(tb.get("chapters", []))
                
                # 表紙画像
                cover_path = DATA_DIR / cover if cover else None
                
                st.markdown(f"**{subject_info['emoji']} {subject_info['name']}**")
                
                if cover_path and cover_path.exists():
                    st.image(str(cover_path), use_container_width=True)
                else:
                    st.markdown("""
                    <div class="cover-placeholder">表紙未登録</div>
                    """, unsafe_allow_html=True)
                
                st.caption(f"📖 {publisher}")
                st.caption(f"📑 {chapters}章")
            else:
                st.markdown(f"**{subject_info['emoji']} {subject_info['name']}**")
                st.markdown("""
                <div class="cover-placeholder">未登録</div>
                """, unsafe_allow_html=True)
    
    # 教科書を選択して目次表示
    st.markdown("---")
    st.markdown("### 📑 目次を見る")
    
    view_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
    view_label = st.selectbox("教科書を選択", list(view_options.keys()), key="view_select")
    view_subject = view_options[view_label]
    
    view_data = load_textbook(view_subject)
    
    if view_data and view_data.get("textbook", {}).get("chapters"):
        chapters = view_data["textbook"]["chapters"]
        
        for chapter in chapters:
            ch_title = f"{chapter.get('chapter_number', '')} {chapter['title']}"
            
            with st.expander(f"📖 {ch_title}"):
                for section in chapter.get("sections", []):
                    st.markdown(f"**{section['title']}**")
                    for sub in section.get("subsections", []):
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.markdown(f"　{sub['title']} (p.{sub['page']})")
                        with col_b:
                            if st.button("💡", key=f"point_{sub['id']}", help="ポイントを見る"):
                                st.session_state.show_point = sub['title']
        
        if "show_point" in st.session_state:
            st.info(f"💡「{st.session_state.show_point}」のポイントを RIA が解説します（予習サポートと連携予定）")
    else:
        st.info(f"{SUBJECTS[view_subject]['name']}の目次はまだ登録されていません")

# ===== サイドバー =====
st.sidebar.markdown("### 📕 教科書登録とは？")
st.sidebar.markdown("""
学校で使う教科書を登録します。

**登録する情報:**
- 📖 出版社名
- 🖼️ 表紙画像
- 📑 目次（別途登録済み）

**登録後:**
- 教科書を選択 → 目次表示
- 章を押す → ポイント解説
""")

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | 教科書登録システム v1.0")
