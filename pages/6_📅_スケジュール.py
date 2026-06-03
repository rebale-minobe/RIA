"""スケジュール画面"""
import streamlit as st
import pandas as pd
from datetime import date
from modules.schedule.manager import (
    get_current_test,
    get_days_until_test,
    mark_task_done,
    get_progress_summary,
)

st.set_page_config(page_title="スケジュール - RIA", page_icon="📅", layout="wide")
st.title("📅 テストスケジュール")

test = get_current_test()
if not test:
    st.info("現在のテスト情報がありません")
    st.stop()

days_left = get_days_until_test()
progress = get_progress_summary()

# ─── サマリー ───
col1, col2, col3, col4 = st.columns(4)
col1.metric("テスト", test['name'])
col2.metric("開始日", test['start_date'])
col3.metric("残り日数", f"{days_left}日" if days_left and days_left > 0 else "—")
col4.metric("計画進捗", f"{progress['percent']}%")

st.progress(progress['percent'] / 100)
st.markdown("---")

# ─── テスト時間割 ───
st.subheader("🗓 テスト時間割")
subjects_data = [
    {
        "日付": s["date"],
        "校時": f"{s.get('period', '')}校時",
        "時間": s.get("time", ""),
        "教科": s["subject_name"],
    }
    for s in test["subjects"]
]
st.dataframe(pd.DataFrame(subjects_data), use_container_width=True, hide_index=True)

# ─── 各教科の試験範囲(展開可能) ───
with st.expander("📋 各教科の試験範囲詳細", expanded=False):
    for s in test["subjects"]:
        st.markdown(f"#### {s['subject_name']}（{s['date']} {s.get('period', '')}校時）")
        st.markdown(f"**範囲:** {s.get('range', '')}")
        if s.get("points"):
            st.markdown(f"**ポイント:** {s['points']}")
        if s.get("submission"):
            st.markdown(f"**提出物:** {s['submission']}")
        st.markdown("---")

# ─── 14日間学習計画 ───
st.subheader("📆 14日間 学習計画")
st.caption("💡 戦略: 社会前倒し（暗記系は早期スタート＋反復で記憶定着）")

today = date.today().isoformat()
for day in test.get("study_plan", []):
    is_today = day["date"] == today
    header = f"**{day['date']}**" + ("　🔵 今日" if is_today else "")
    with st.container(border=True):
        st.markdown(header)
        for i, task in enumerate(day.get("tasks", [])):
            checked = st.checkbox(
                f"**{task['subject_name']}** — {task['topic']}　（{task['duration_min']}分）",
                value=task.get("done", False),
                key=f"sched_task_{day['date']}_{i}",
            )
            if checked != task.get("done", False):
                mark_task_done(day["date"], i, checked)
                st.rerun()
