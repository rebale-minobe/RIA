"""
RIA 教科書管理システム
教科書の目次を表示 → 「今日学んだ範囲」を記録 → 進捗を可視化
教科に依存しない設計（社会・国語・数学... どれでも対応可能）
"""

import streamlit as st
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ===== ページ設定 =====
st.set_page_config(page_title="📚 教科書管理", layout="wide")

# ===== スタイル =====
st.markdown("""
<style>
    .chapter-header {
        background: linear-gradient(90deg, #4a90e2 0%, #357abd 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 18px;
        margin: 15px 0 10px 0;
    }
    .section-item {
        background-color: #f0f4ff;
        padding: 10px 15px;
        border-radius: 6px;
        border-left: 4px solid #4a90e2;
        margin: 8px 0;
    }
    .progress-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #e9ecef;
    }
    .studied-badge {
        background-color: #28a745;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin-left: 8px;
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

# ===== データ読み込み =====

@st.cache_data(ttl=300)
def load_textbook(subject_key: str):
    """
    教科書の目次データを読み込む
    GitHub → ローカル → フォールバック の順
    """
    textbook_file = SUBJECTS[subject_key]["textbook_file"]
    
    # GitHub から読み込み
    try:
        url = f"https://raw.githubusercontent.com/rebale-minobe/RIA/main/data/{textbook_file}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # ローカルから読み込み
    local_path = Path(__file__).parent.parent / "data" / textbook_file
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None

def load_study_records(subject_key: str):
    """
    学習記録を読み込む
    """
    records_path = Path("data/textbook_progress") / f"{subject_key}.json"
    
    if records_path.exists():
        with open(records_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {"studied_sections": [], "daily_notes": []}

def save_study_record(subject_key: str, section_id: str, section_title: str, note: str = ""):
    """
    学習記録を保存
    """
    records_path = Path("data/textbook_progress")
    records_path.mkdir(parents=True, exist_ok=True)
    
    file_path = records_path / f"{subject_key}.json"
    
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    else:
        records = {"studied_sections": [], "daily_notes": []}
    
    # 学習済みセクションに追加（重複チェック）
    today = datetime.now().strftime("%Y-%m-%d")
    
    study_entry = {
        "section_id": section_id,
        "section_title": section_title,
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "note": note
    }
    
    records["studied_sections"].append(study_entry)
    
    # 日次メモに追加
    if note:
        records["daily_notes"].append({
            "date": today,
            "section_title": section_title,
            "note": note,
            "timestamp": datetime.now().isoformat()
        })
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    return True

# ===== メイン UI =====

st.title("📚 教科書管理")
st.write("今日学んだ範囲を記録して、進捗を確認しましょう！")

# 教科選択
subject_options = {f"{v['emoji']} {v['name']}": k for k, v in SUBJECTS.items()}
selected_subject_label = st.selectbox("教科を選択", list(subject_options.keys()))
selected_subject = subject_options[selected_subject_label]

# 教科書データを読み込み
textbook_data = load_textbook(selected_subject)

if not textbook_data:
    st.warning(f"⏳ {SUBJECTS[selected_subject]['name']}の教科書データがまだ登録されていません。")
    st.info("教科書の目次を登録すると、ここに表示されます。")
    st.stop()

# 学習記録を読み込み
study_records = load_study_records(selected_subject)
studied_section_ids = [s["section_id"] for s in study_records["studied_sections"]]

# ===== 進捗ダッシュボード =====

st.markdown("---")

# 全セクション数をカウント
total_sections = 0
for chapter in textbook_data["textbook"]["chapters"]:
    for section in chapter.get("sections", []):
        for subsection in section.get("subsections", []):
            total_sections += 1

studied_count = len(set(studied_section_ids))
progress_pct = (studied_count / total_sections * 100) if total_sections > 0 else 0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="progress-card">
        <div style="font-size: 14px; color: #666;">学習済みセクション</div>
        <div style="font-size: 36px; font-weight: bold; color: #4a90e2;">{studied_count}/{total_sections}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="progress-card">
        <div style="font-size: 14px; color: #666;">進捗率</div>
        <div style="font-size: 36px; font-weight: bold; color: #28a745;">{progress_pct:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # 今日の学習数
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = len([s for s in study_records["studied_sections"] if s["date"] == today])
    st.markdown(f"""
    <div class="progress-card">
        <div style="font-size: 14px; color: #666;">今日の学習</div>
        <div style="font-size: 36px; font-weight: bold; color: #ff6b6b;">{today_count} 件</div>
    </div>
    """, unsafe_allow_html=True)

# プログレスバー
st.progress(progress_pct / 100)

# ===== 学習記録の入力 =====

st.markdown("---")
st.markdown("## 📝 今日学んだ範囲を記録")

# 章を選択
chapters = textbook_data["textbook"]["chapters"]
chapter_options = {
    f"{ch.get('chapter_number', '')} {ch['title']}": ch
    for ch in chapters
}

selected_chapter_label = st.selectbox(
    "📖 章を選択",
    list(chapter_options.keys())
)
selected_chapter = chapter_options[selected_chapter_label]

# 節を選択
sections = selected_chapter.get("sections", [])
if sections:
    section_options = {
        f"{sec['title']}": sec
        for sec in sections
    }
    selected_section_label = st.selectbox(
        "📑 節を選択",
        list(section_options.keys())
    )
    selected_section = section_options[selected_section_label]
    
    # 小節を選択（あれば）
    subsections = selected_section.get("subsections", [])
    if subsections:
        st.markdown("**学んだ小節を選択（複数可）:**")
        
        selected_subs = []
        for sub in subsections:
            is_studied = sub["id"] in studied_section_ids
            label = f"{sub['title']} (p.{sub['page']})"
            if is_studied:
                label += " ✅"
            
            if st.checkbox(label, key=f"sub_{sub['id']}"):
                selected_subs.append(sub)
        
        # メモ入力
        note = st.text_area("📝 今日の振り返りメモ（任意）", placeholder="例: 縄文時代の生活がよく分かった。土器の種類を覚える。")
        
        # 記録ボタン
        if st.button("✅ 学習を記録", type="primary", use_container_width=True):
            if selected_subs:
                for sub in selected_subs:
                    save_study_record(
                        selected_subject,
                        sub["id"],
                        sub["title"],
                        note
                    )
                st.success(f"🎉 {len(selected_subs)} 件の学習を記録しました！")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("学んだ小節を選択してください")

# ===== 学習履歴 =====

st.markdown("---")
st.markdown("## 📊 学習履歴")

if study_records["studied_sections"]:
    # 日付ごとにグループ化
    from collections import defaultdict
    by_date = defaultdict(list)
    for s in study_records["studied_sections"]:
        by_date[s["date"]].append(s)
    
    # 新しい順に表示
    for date in sorted(by_date.keys(), reverse=True)[:7]:  # 直近7日
        st.markdown(f"### 📅 {date}")
        for s in by_date[date]:
            note_text = f" — 💭 {s['note']}" if s.get('note') else ""
            st.markdown(f"- ✅ {s['section_title']}{note_text}")
else:
    st.info("まだ学習記録がありません。上で記録を始めましょう！")

# ===== サイドバー =====

st.sidebar.markdown("### 📚 教科書情報")
st.sidebar.write(f"**教科**: {SUBJECTS[selected_subject]['name']}")
st.sidebar.write(f"**教科書**: {textbook_data['textbook'].get('name', '未設定')}")
st.sidebar.write(f"**総ページ数**: {textbook_data['textbook'].get('total_pages', '?')}")
st.sidebar.write(f"**章数**: {len(chapters)}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 使い方")
st.sidebar.markdown("""
1. 教科を選ぶ
2. 今日学んだ章・節を選択
3. 振り返りメモを書く
4. 「学習を記録」をクリック
5. 進捗が自動更新！
""")

# ===== フッター =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
RIA — Ria's Intelligent Agent | 教科書管理システム v1.0
</div>
""", unsafe_allow_html=True)
