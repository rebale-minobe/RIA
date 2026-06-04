"""
RIA TOP ページ（モック v0.2）
更新点:
- ヘッダー削除（スッキリ）
- NEXT TEST: テスト範囲詳細 + 勉強時間
- 今日の時間割: 教科書タイトルから今日やった範囲を選択
"""

import streamlit as st
from datetime import datetime, timedelta

# ===== ページ設定 =====
st.set_page_config(
    page_title="RIA",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== スタイル =====
st.markdown("""
<style>
    .ria-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #f0f0f0;
    }
    .test-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white;
        border-radius: 16px;
        padding: 28px;
        text-align: center;
    }
    .countdown-number {
        font-size: 64px;
        font-weight: 800;
        line-height: 1;
        margin: 8px 0;
    }
    .period-row {
        display: flex;
        padding: 10px 14px;
        border-radius: 8px;
        margin: 6px 0;
        background: #f8f9fa;
        align-items: center;
    }
    .period-num {
        background: #4a90e2;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-weight: bold;
        margin-right: 12px;
    }
    .section-title {
        font-size: 22px;
        font-weight: 700;
        margin: 24px 0 12px 0;
        color: #2c3e50;
    }
    .range-item {
        background: #fff8f8;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #ff6b6b;
        margin: 8px 0;
    }
    .study-time-badge {
        background: #4a90e2;
        color: white;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ===== ダミーデータ =====

# テスト情報（範囲 + 推奨勉強時間つき）
NEXT_TEST = {
    "name": "1学期 期末テスト",
    "start_date": "2026-06-18",
    "subjects": [
        {"subject": "技術家庭", "date": "6/18(木)", "time": "9:00", "range": "教科書 P30-55", "study_hours": 2},
        {"subject": "国語", "date": "6/18(木)", "time": "9:45", "range": "漢字 + 文法（助動詞）+ 読解「故郷」", "study_hours": 5},
        {"subject": "社会", "date": "6/18(木)", "time": "10:45", "range": "歴史 P105-160（武家政権〜江戸）", "study_hours": 8},
        {"subject": "保健体育", "date": "6/18(木)", "time": "11:45", "range": "教科書 P20-40", "study_hours": 2},
        {"subject": "数学", "date": "6/19(金)", "time": "9:00", "range": "1年範囲復習 + 文章題 + 連立方程式", "study_hours": 12},
        {"subject": "英語", "date": "6/19(金)", "time": "10:00", "range": "Unit 1-3 + 英作文 + 不規則動詞", "study_hours": 3},
        {"subject": "理科", "date": "6/19(金)", "time": "10:55", "range": "化学変化 + 生物のからだ", "study_hours": 4},
    ]
}

TODO_TODAY = [
    {"subject": "🗺️ 社会", "task": "歴史 P105-130 教科書通読", "duration": "60分", "done": False},
    {"subject": "📐 数学", "task": "1年範囲 P225-248 復習", "duration": "30分", "done": False},
    {"subject": "📘 国語", "task": "漢字テスト範囲 10個", "duration": "20分", "done": True},
]

# 今日の時間割（教科書範囲選択用に、教科書セクションを紐付け）
TODAY_TIMETABLE = [
    {"period": 1, "subject": "国語", "subject_key": "japanese"},
    {"period": 2, "subject": "数学", "subject_key": "math"},
    {"period": 3, "subject": "社会", "subject_key": "social"},
    {"period": 4, "subject": "理科", "subject_key": "science"},
    {"period": 5, "subject": "英語", "subject_key": "english"},
    {"period": 6, "subject": "音楽", "subject_key": "music"},
]

# 社会教科書の章・節（today timetable で選択用、本番は JSON から）
SOCIAL_SECTIONS = [
    "第3章 第1節 武士の世の始まり",
    "第3章 第2節 武家政権の内と外",
    "第4章 第1節 大航海によって結びつく世界",
    "第4章 第2節 戦乱から全国統一へ",
    "第4章 第3節 武士による全国支配の完成",
]

TOMORROW_TIMETABLE = [
    {"period": 1, "subject": "数学", "next_chapter": "連立方程式の応用", "page": "P232"},
    {"period": 2, "subject": "社会", "next_chapter": "江戸幕府の成立", "page": "P124"},
    {"period": 3, "subject": "保健体育", "next_chapter": "運動と健康", "page": "P25"},
    {"period": 4, "subject": "国語", "next_chapter": "古文入門", "page": "P88"},
    {"period": 5, "subject": "技術", "next_chapter": "木材加工", "page": "P40"},
    {"period": 6, "subject": "英語", "next_chapter": "Unit 4 - 未来形", "page": "P45"},
]

# ===== カウントダウン計算 =====

today = datetime.now()
test_date = datetime.strptime(NEXT_TEST["start_date"], "%Y-%m-%d")
days_until_test = (test_date - today).days

# ===== レイアウト =====

col_left, col_right = st.columns([3, 2])

# ===== 左カラム =====

with col_left:
    # --- 1. NEXT TEST ---
    st.markdown('<div class="section-title">⏳ NEXT TEST</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="test-card">
        <div style="font-size: 18px; opacity: 0.9;">{NEXT_TEST['name']} まで</div>
        <div class="countdown-number">{days_until_test}</div>
        <div style="font-size: 20px;">日</div>
        <div style="font-size: 14px; opacity: 0.8; margin-top: 8px;">開始: {NEXT_TEST['start_date']}（木）</div>
    </div>
    """, unsafe_allow_html=True)
    
    # テスト範囲詳細 + 勉強時間
    st.markdown("#### 📋 テスト範囲と勉強時間")
    
    total_hours = sum(s["study_hours"] for s in NEXT_TEST["subjects"])
    st.markdown(f"**推奨勉強時間 合計: {total_hours} 時間**　（残り {days_until_test} 日 → 1日 約{total_hours/max(days_until_test,1):.1f}時間）")
    
    for s in NEXT_TEST["subjects"]:
        st.markdown(f"""
        <div class="range-item">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong>{s['subject']}</strong>
                <span class="study-time-badge">⏱ {s['study_hours']}h</span>
            </div>
            <div style="font-size: 13px; color: #666; margin-top: 4px;">
                📅 {s['date']} {s['time']}<br>
                📖 {s['range']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- 2. To Do TODAY ---
    st.markdown('<div class="section-title">📌 To Do TODAY</div>', unsafe_allow_html=True)
    
    done_count = sum(1 for t in TODO_TODAY if t["done"])
    st.markdown(f"今日のタスク: **{done_count}/{len(TODO_TODAY)}** 完了")
    
    for i, todo in enumerate(TODO_TODAY):
        st.checkbox(
            f"{todo['subject']} — {todo['task']}（{todo['duration']}）",
            value=todo["done"],
            key=f"todo_{i}"
        )
    
    st.caption("💡 To Do は RIA が「テストまでの日数 + 進捗 + 苦手」から自動生成（予定）")

# ===== 右カラム =====

with col_right:
    # --- 3. 今日の時間割（教科書範囲選択）---
    st.markdown('<div class="section-title">📅 今日の時間割</div>', unsafe_allow_html=True)
    st.caption("各授業で「今日やった範囲」を教科書から選択できます")
    
    for p in TODAY_TIMETABLE:
        with st.container():
            st.markdown(f"""
            <div class="period-row">
                <span class="period-num">{p['period']}</span>
                <span><strong>{p['subject']}</strong></span>
            </div>
            """, unsafe_allow_html=True)
            
            # 社会だけ範囲選択を実装（モック）
            if p["subject_key"] == "social":
                selected_range = st.selectbox(
                    f"今日やった範囲（{p['subject']}）",
                    ["（未選択）"] + SOCIAL_SECTIONS,
                    key=f"range_{p['period']}",
                    label_visibility="collapsed"
                )
                if selected_range != "（未選択）":
                    if st.button(f"✅ 記録", key=f"rec_{p['period']}"):
                        st.success(f"記録: {selected_range}")

# ===== 明日の時間割 =====

st.markdown('<div class="section-title">🔮 明日の時間割（予習プレビュー）</div>', unsafe_allow_html=True)

cols = st.columns(3)
for i, p in enumerate(TOMORROW_TIMETABLE):
    with cols[i % 3]:
        st.markdown(f"""
        <div class="ria-card" style="padding: 16px;">
            <div style="color: #888; font-size: 13px;">{p['period']}限</div>
            <div style="font-size: 18px; font-weight: bold; color: #4a90e2;">{p['subject']}</div>
            <div style="font-size: 14px; margin: 6px 0;">📖 {p['next_chapter']}</div>
            <div style="color: #888; font-size: 12px;">{p['page']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"💡 ポイントを見る", key=f"point_{i}"):
            st.info(f"「{p['next_chapter']}」のポイントを RIA が解説（実装予定）")

# ===== Study =====

st.markdown('<div class="section-title">📚 Study</div>', unsafe_allow_html=True)
st.markdown("各教科の教科書・ワークで学習できます")

study_cols = st.columns(5)
subjects = [
    {"emoji": "📘", "name": "国語"},
    {"emoji": "🗺️", "name": "社会"},
    {"emoji": "📐", "name": "数学"},
    {"emoji": "🔬", "name": "理科"},
    {"emoji": "🌐", "name": "英語"},
]

for i, subj in enumerate(subjects):
    with study_cols[i]:
        if st.button(f"{subj['emoji']} {subj['name']}", key=f"study_{i}", use_container_width=True):
            st.session_state.selected_study = subj["name"]

if "selected_study" in st.session_state:
    st.markdown("---")
    st.markdown(f"### {st.session_state.selected_study} の学習メニュー")
    menu_col1, menu_col2 = st.columns(2)
    with menu_col1:
        st.markdown("""
        <div class="ria-card" style="text-align: center;">
            <div style="font-size: 32px;">📖</div>
            <div style="font-weight: bold; font-size: 18px;">教科書</div>
            <div style="color: #888; font-size: 13px;">目次 → 章 → ポイント</div>
        </div>
        """, unsafe_allow_html=True)
    with menu_col2:
        st.markdown("""
        <div class="ria-card" style="text-align: center;">
            <div style="font-size: 32px;">📝</div>
            <div style="font-weight: bold; font-size: 18px;">ワーク</div>
            <div style="color: #888; font-size: 13px;">問題 → 答え → 解説</div>
        </div>
        """, unsafe_allow_html=True)

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | TOP ページ モック v0.2")
