"""
RIA TOP ページ（モック版）
5つのコンテンツ:
1. NEXT TEST（カウントダウン）
2. To Do TODAY
3. 今日の時間割
4. 明日の時間割
5. Study（教科ハブ）

※ ダミーデータで動作確認用。仕様調整後に実データ連携。
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
    /* カード共通 */
    .ria-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #f0f0f0;
    }
    /* NEXT TEST カード */
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
    /* To Do カード */
    .todo-item {
        background: #f8f9fa;
        padding: 14px 18px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid #4a90e2;
        display: flex;
        align-items: center;
    }
    /* 時間割 */
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
    /* Study ボタン */
    .study-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ===== ダミーデータ =====

# テスト情報
NEXT_TEST = {
    "name": "1学期 期末テスト",
    "start_date": "2026-06-18",
    "subjects": [
        {"subject": "技術家庭", "date": "6/18(木)", "time": "9:00", "range": "教科書 P30-55"},
        {"subject": "国語", "date": "6/18(木)", "time": "9:45", "range": "漢字 + 文法 + 読解"},
        {"subject": "社会", "date": "6/18(木)", "time": "10:45", "range": "歴史 P105-160"},
        {"subject": "保健体育", "date": "6/18(木)", "time": "11:45", "range": "教科書 P20-40"},
        {"subject": "数学", "date": "6/19(金)", "time": "9:00", "range": "1年範囲 + 文章題"},
        {"subject": "英語", "date": "6/19(金)", "time": "10:00", "range": "Unit 1-3 + 英作文"},
        {"subject": "理科", "date": "6/19(金)", "time": "10:55", "range": "化学変化 + 生物"},
    ]
}

# 今日のTo Do（AI生成想定）
TODO_TODAY = [
    {"subject": "🗺️ 社会", "task": "歴史 P105-130 教科書通読", "duration": "60分", "done": False},
    {"subject": "📐 数学", "task": "1年範囲 P225-248 復習", "duration": "30分", "done": False},
    {"subject": "📘 国語", "task": "漢字テスト範囲 10個", "duration": "20分", "done": True},
]

# 今日の時間割
TODAY_TIMETABLE = [
    {"period": 1, "subject": "国語", "content": "文法 - 助動詞"},
    {"period": 2, "subject": "数学", "content": "文章題の解き方"},
    {"period": 3, "subject": "社会", "content": "織豊政権"},
    {"period": 4, "subject": "理科", "content": "化学変化"},
    {"period": 5, "subject": "英語", "content": "Unit 3 - 過去形"},
    {"period": 6, "subject": "音楽", "content": "合唱練習"},
]

# 明日の時間割
TOMORROW_TIMETABLE = [
    {"period": 1, "subject": "数学", "next_chapter": "連立方程式の応用", "page": "P232"},
    {"period": 2, "subject": "社会", "next_chapter": "江戸幕府の成立", "page": "P124"},
    {"period": 3, "subject": "保健体育", "next_chapter": "運動と健康", "page": "P25"},
    {"period": 4, "subject": "国語", "next_chapter": "古文入門", "page": "P88"},
    {"period": 5, "subject": "技術", "next_chapter": "木材加工", "page": "P40"},
    {"period": 6, "subject": "英語", "next_chapter": "Unit 4 - 未来形", "page": "P45"},
]

# ===== ヘッダー =====

today = datetime.now()
test_date = datetime.strptime(NEXT_TEST["start_date"], "%Y-%m-%d")
days_until_test = (test_date - today).days

st.markdown("# 🌟 RIA")
st.markdown("##### Ria's Intelligent Agent — 莉亜の学習エージェント")
st.markdown(f"こんにちは、**見延 莉亜** さん！　📅 {today.strftime('%Y年%m月%d日')}")

st.markdown("---")

# ===== レイアウト：左カラム（メイン）+ 右カラム =====

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
    
    # テスト詳細（展開）
    with st.expander("📋 テストの詳細を見る"):
        for s in NEXT_TEST["subjects"]:
            st.markdown(f"""
            **{s['subject']}** — {s['date']} {s['time']}  
            　範囲: {s['range']}
            """)
    
    # --- 2. To Do TODAY ---
    st.markdown('<div class="section-title">📌 To Do TODAY</div>', unsafe_allow_html=True)
    
    done_count = sum(1 for t in TODO_TODAY if t["done"])
    st.markdown(f"今日のタスク: **{done_count}/{len(TODO_TODAY)}** 完了")
    
    for i, todo in enumerate(TODO_TODAY):
        checked = st.checkbox(
            f"{todo['subject']} — {todo['task']}（{todo['duration']}）",
            value=todo["done"],
            key=f"todo_{i}"
        )
    
    st.caption("💡 To Do は RIA が「テストまでの日数 + 進捗 + 苦手」から自動生成（予定）")

# ===== 右カラム =====

with col_right:
    # --- 3. 今日の時間割 ---
    st.markdown('<div class="section-title">📅 今日の時間割</div>', unsafe_allow_html=True)
    
    for p in TODAY_TIMETABLE:
        st.markdown(f"""
        <div class="period-row">
            <span class="period-num">{p['period']}</span>
            <span><strong>{p['subject']}</strong> — {p['content']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("✏️ 今日やったことを記録"):
        st.text_input("教科書ページ数", placeholder="例: 社会 P105-110")
        st.text_input("出た宿題", placeholder="例: ワーク P20-22")
        st.button("記録する", key="record_today")

# ===== 下段：明日の時間割（全幅）=====

st.markdown('<div class="section-title">🔮 明日の時間割（予習プレビュー）</div>', unsafe_allow_html=True)

cols = st.columns(3)
for i, p in enumerate(TOMORROW_TIMETABLE):
    with cols[i % 3]:
        with st.container():
            st.markdown(f"""
            <div class="ria-card" style="padding: 16px;">
                <div style="color: #888; font-size: 13px;">{p['period']}限</div>
                <div style="font-size: 18px; font-weight: bold; color: #4a90e2;">{p['subject']}</div>
                <div style="font-size: 14px; margin: 6px 0;">📖 {p['next_chapter']}</div>
                <div style="color: #888; font-size: 12px;">{p['page']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"💡 ポイントを見る", key=f"point_{i}"):
                st.info(f"「{p['next_chapter']}」のポイントを RIA が解説します（実装予定）")

# ===== Study（教科ハブ）=====

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
        if st.button(f"{subj['emoji']}\n\n{subj['name']}", key=f"study_{i}", use_container_width=True):
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
st.caption("🌟 RIA — Ria's Intelligent Agent | TOP ページ モック v0.1（ダミーデータ）")
