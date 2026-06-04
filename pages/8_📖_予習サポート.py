"""
RIA 予習サポートシステム（予習の予習）
教科書の難しい言葉の前に、RIA が易しい要点を生成
→ 概要を掴んでから本読みを始める
→ 予習を記録して学習資産にする
"""

import streamlit as st
import json
import requests
from datetime import datetime
from pathlib import Path

# ===== ページ設定 =====
st.set_page_config(page_title="📖 予習サポート", layout="wide")

# ===== スタイル =====
st.markdown("""
<style>
    .preview-box {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cc 100%);
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid #ffa500;
        margin: 20px 0;
        line-height: 1.8;
    }
    .step-badge {
        background-color: #4a90e2;
        color: white;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 13px;
        font-weight: bold;
    }
    .completed-badge {
        background-color: #28a745;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ===== 教科設定 =====

SUBJECTS = {
    "social": {"name": "社会", "emoji": "🗺️", "textbook_file": "social_textbook.json"},
    "japanese": {"name": "国語", "emoji": "📘", "textbook_file": "japanese_textbook.json"},
    "science": {"name": "理科", "emoji": "🔬", "textbook_file": "science_textbook.json"},
}

# ===== データ読み込み =====

@st.cache_data(ttl=300)
def load_textbook(subject_key: str):
    """教科書の目次データを読み込む"""
    textbook_file = SUBJECTS[subject_key]["textbook_file"]
    
    try:
        url = f"https://raw.githubusercontent.com/rebale-minobe/RIA/main/data/{textbook_file}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    local_path = Path(__file__).parent.parent / "data" / textbook_file
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None

def load_preparation_records(subject_key: str):
    """予習記録を読み込む"""
    records_path = Path("data/preparation_records") / f"{subject_key}.json"
    
    if records_path.exists():
        with open(records_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return []

def save_preparation_record(subject_key: str, section_id: str, section_title: str, ria_summary: str):
    """予習記録を保存"""
    records_path = Path("data/preparation_records")
    records_path.mkdir(parents=True, exist_ok=True)
    
    file_path = records_path / f"{subject_key}.json"
    
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    else:
        records = []
    
    record = {
        "section_id": section_id,
        "section_title": section_title,
        "ria_summary": ria_summary,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }
    
    records.append(record)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    return True

def generate_preview_summary(subject_name: str, chapter_title: str, section_title: str, subsection_title: str) -> str:
    """
    RIA（Claude）が単元の要点を生成（予習の予習）
    """
    try:
        from shared.claude_client import ClaudeClient
        
        claude_client = ClaudeClient()
        
        prompt = f"""
中学2年生の莉亜さんが、{subject_name}の教科書を読む前の「予習の予習」をします。

【これから読む単元】
- 章: {chapter_title}
- 節: {section_title}
- 小節: {subsection_title}

【あなたの役割】
教科書は言葉が難しいので、莉亜さんが教科書を読む前に、この単元の要点を易しく説明してください。

【要点の構成】
1. 📌 **この単元のテーマ**（1-2文で「何を学ぶか」）
2. 🔑 **重要キーワード**（3-5個、それぞれ簡単な説明つき）
3. 📖 **ストーリーで理解**（この時代/出来事を、わかりやすい物語として2-3段落で）
4. 💡 **ここがポイント**（テストで問われやすい点、覚えるべきこと）
5. ❓ **読みながら考えてみよう**（教科書を読むときの問いを1-2個）

【トーン】
- 中学生に語りかけるように、親しみやすく
- 難しい言葉は使わず、使うときは説明を添える
- 「なるほど！」と思える具体例やたとえを使う
- 莉亜さんが「教科書、読んでみよう」とワクワクするように

要点を作成してください。
"""
        
        # Claude API 呼び出し
        response = claude_client.call_api(
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response
    
    except Exception as e:
        return f"""
要点の生成中にエラーが発生しました。

エラー詳細: {str(e)[:100]}

もう一度お試しください。問題が続く場合は、APIキーの設定を確認してください。
"""

# ===== セッション状態 =====

if "preview_summary" not in st.session_state:
    st.session_state.preview_summary = None

if "current_section_info" not in st.session_state:
    st.session_state.current_section_info = None

# ===== メイン UI =====

st.title("📖 予習サポート")
st.markdown("**「予習の予習」** — 教科書を読む前に、RIA が要点を易しく解説します！")

# 教科選択
subject_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
selected_subject_label = st.selectbox("教科を選択", list(subject_options.keys()))
selected_subject = subject_options[selected_subject_label]
subject_name = SUBJECTS[selected_subject]["name"]

# 教科書データ読み込み
textbook_data = load_textbook(selected_subject)

if not textbook_data:
    st.warning(f"⏳ {subject_name}の教科書データがまだ登録されていません。")
    st.stop()

# 予習記録を読み込み
prep_records = load_preparation_records(selected_subject)
prepared_section_ids = [r["section_id"] for r in prep_records]

# ===== 単元選択 =====

st.markdown("---")
st.markdown("## 1️⃣ 今日読む単元を選ぼう")

chapters = textbook_data["textbook"]["chapters"]

# 章選択
chapter_options = {
    f"{ch.get('chapter_number', '')} {ch['title']}": ch
    for ch in chapters
}
selected_chapter_label = st.selectbox("📖 章", list(chapter_options.keys()))
selected_chapter = chapter_options[selected_chapter_label]

# 節選択
sections = selected_chapter.get("sections", [])
if sections:
    section_options = {sec['title']: sec for sec in sections}
    selected_section_label = st.selectbox("📑 節", list(section_options.keys()))
    selected_section = section_options[selected_section_label]
    
    # 小節選択
    subsections = selected_section.get("subsections", [])
    if subsections:
        subsection_options = {}
        for sub in subsections:
            label = f"{sub['title']} (p.{sub['page']})"
            if sub["id"] in prepared_section_ids:
                label += " ✅予習済"
            subsection_options[label] = sub
        
        selected_subsection_label = st.selectbox("📝 小節", list(subsection_options.keys()))
        selected_subsection = subsection_options[selected_subsection_label]
        
        # ===== 予習の予習ボタン =====
        
        st.markdown("---")
        st.markdown("## 2️⃣ RIA に要点を聞こう")
        
        if st.button("🌟 予習の予習をする（RIA に要点を聞く）", type="primary", use_container_width=True):
            with st.spinner("RIA が要点を作成中... ✍️"):
                summary = generate_preview_summary(
                    subject_name=subject_name,
                    chapter_title=selected_chapter["title"],
                    section_title=selected_section["title"],
                    subsection_title=selected_subsection["title"]
                )
                st.session_state.preview_summary = summary
                st.session_state.current_section_info = {
                    "section_id": selected_subsection["id"],
                    "section_title": selected_subsection["title"],
                    "page": selected_subsection["page"]
                }
        
        # ===== 要点表示 =====
        
        if st.session_state.preview_summary:
            st.markdown("---")
            st.markdown("## 3️⃣ RIA からの要点")
            
            st.markdown(f"""
            <div class="preview-box">
            {st.session_state.preview_summary}
            </div>
            """, unsafe_allow_html=True)
            
            # 教科書読み開始の案内
            page = st.session_state.current_section_info["page"]
            st.success(f"📖 要点を掴んだら、教科書 **p.{page}** を開いて読み始めよう！")
            
            # ===== 予習完了ボタン =====
            
            st.markdown("---")
            st.markdown("## 4️⃣ 予習を記録")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ 予習完了（記録する）", type="primary", use_container_width=True):
                    save_preparation_record(
                        selected_subject,
                        st.session_state.current_section_info["section_id"],
                        st.session_state.current_section_info["section_title"],
                        st.session_state.preview_summary
                    )
                    st.success("🎉 予習を記録しました！この調子で頑張ろう！")
                    st.balloons()
                    # リセット
                    st.session_state.preview_summary = None
                    st.cache_data.clear()
            
            with col2:
                if st.button("🔄 別の要点を聞く", use_container_width=True):
                    st.session_state.preview_summary = None
                    st.rerun()

# ===== 予習履歴 =====

st.markdown("---")
st.markdown("## 📊 予習の記録")

if prep_records:
    st.write(f"これまでに **{len(prep_records)} 件** の予習を完了しました！")
    
    # 日付ごとにグループ化
    from collections import defaultdict
    by_date = defaultdict(list)
    for r in prep_records:
        by_date[r["date"]].append(r)
    
    for date in sorted(by_date.keys(), reverse=True)[:5]:
        st.markdown(f"### 📅 {date}")
        for r in by_date[date]:
            with st.expander(f"✅ {r['section_title']}"):
                st.markdown(r["ria_summary"])
else:
    st.info("まだ予習記録がありません。上で予習を始めましょう！")

# ===== サイドバー =====

st.sidebar.markdown("### 📖 予習サポートとは？")
st.sidebar.markdown("""
教科書は言葉が難しいので、
**読む前に RIA が要点を解説**します。

1. 単元を選ぶ
2. RIA に要点を聞く
3. 概要を掴む
4. 教科書を読む
5. 予習を記録

**「予習の予習」で理解度アップ！**
""")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### 📊 {subject_name}の予習状況")
st.sidebar.write(f"**予習完了**: {len(prep_records)} 件")

# ===== フッター =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
RIA — Ria's Intelligent Agent | 予習サポートシステム v1.0
</div>
""", unsafe_allow_html=True)
