"""
RIA - Ria's Intelligent Agent
ホーム画面: 期末カウントダウン + 今日のミッション + 6つの入口
"""
import streamlit as st
from datetime import date
from modules.schedule.manager import (
    get_current_test,
    get_days_until_test,
    get_today_tasks,
    get_progress_summary,
    mark_task_done,
)
from shared.profile import get_profile

st.set_page_config(
    page_title="RIA - Ria's Intelligent Agent",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── ヘッダー ───
st.title("🌟 RIA")
st.caption("Ria's Intelligent Agent — 莉亜の学習エージェント")

profile = get_profile()
st.markdown(f"こんにちは、**{profile.data['name']}** さん！")
st.caption(f"🎯 夢: {profile.data['dream']}")

st.markdown("---")

# ─── 期末カウントダウン & 全体進捗 ───
test = get_current_test()
days_left = get_days_until_test()
progress = get_progress_summary()

if test and days_left is not None:
    col1, col2, col3 = st.columns(3)
    with col1:
        if days_left > 0:
            st.metric(f"⏳ {test['name']}まで", f"{days_left}日")
        elif days_left == 0:
            st.metric(f"📍 {test['name']}", "今日！")
        else:
            st.metric(test['name'], "終了")
    with col2:
        st.metric("📅 テスト日程", f"{test['start_date']} 〜 {test['end_date']}")
    with col3:
        st.metric("✅ 学習計画 進捗", f"{progress['done']} / {progress['total']}",
                  delta=f"{progress['percent']}%")

    st.progress(progress['percent'] / 100)

st.markdown("---")

# ─── 今日のミッション ───
st.subheader("📌 今日のミッション")
today_str = date.today().isoformat()
st.caption(f"日付: {today_str}")

today_tasks = get_today_tasks()
if today_tasks:
    for i, task in enumerate(today_tasks):
        done_status = st.checkbox(
            f"**{task['subject_name']}** — {task['topic']} （{task['duration_min']}分）",
            value=task.get("done", False),
            key=f"home_task_{i}",
        )
        if done_status != task.get("done", False):
            mark_task_done(today_str, i, done_status)
            st.rerun()
else:
    st.info("今日のタスクは設定されていません。スケジュールページで確認・追加できます。")

st.markdown("---")

# ─── 学習入口 ───
st.subheader("📚 学習を始める")
st.caption("👈 サイドバーから教科ページを開いてください")

entries = [
    ("📘", "国語", "漢字・読解・古文・記述"),
    ("🗺️", "社会", "歴史・暗記・因果関係"),
    ("📐", "数学", "応用思考・解法言語化"),
    ("🔬", "理科", "概念学習・実験考察"),
    ("🌐", "英語", "英作文・英検準2級準備"),
    ("📅", "スケジュール", "計画・進捗・カウントダウン"),
]
cols = st.columns(3)
for i, (icon, name, desc) in enumerate(entries):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {icon} {name}")
            st.caption(desc)

# ─── フッター ───
st.markdown("---")
with st.expander("ℹ️ RIAについて"):
    st.markdown(f"""
    **RIA (Ria's Intelligent Agent)** は莉亜さん専用の学習エージェントです。

    - **タイプ**: {profile.data['type_diagnosis']}
    - **アプローチ**: 答えを教えるより、自分の言葉で説明させる対話
    - **次のテスト**: {test['name'] if test else '未設定'}

    詳細は Obsidian の `20_Projects/RIA/` を参照。
    """)
