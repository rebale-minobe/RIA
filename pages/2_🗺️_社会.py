"""社会ページ"""
import streamlit as st
from shared.ui import render_subject_page
from shared.answer_log_hierarchy import AnswerLogPivot

st.set_page_config(page_title="社会 - RIA", page_icon="🗺️", layout="wide")
render_subject_page("social", "社会", "🗺️")

# ========== ワーク再TEST セクション
st.markdown("---")
st.subheader("🔄 ワーク再TEST")
st.caption("最近の誤答問題を集中復習")

# キャッシュで CSV を読み込み（毎日1回だけ）
@st.cache_data(ttl=86400)  # 24時間
def load_answer_log():
    try:
        csv_path = "data/answer_log_social_pivot.csv"
        return AnswerLogPivot.load_csv(csv_path)
    except FileNotFoundError:
        st.error(f"❌ {csv_path} が見つかりません")
        return None

log = load_answer_log()
if not log:
    st.stop()

# ========== ① 章を選択
chapters = log.get_chapters()
if not chapters:
    st.warning("まだ再TEST対象がありません")
    st.stop()

chapter_num, chapter_title = st.selectbox(
    "章を選択",
    chapters,
    format_func=lambda x: f"{x[0]} {x[1]}",
    key="retest_chapter_social"
)

# ========== ② lesson_title を選択（進捗表示付き）
lessons = log.get_lessons_in_chapter(chapter_num)

st.markdown("**📖 この章の単元**")
lesson_options = []
for lesson in lessons:
    total = lesson['total_count']
    maru = lesson['maru_count']
    batsu = lesson['batsu_count']
    
    if batsu > 0:
        progress = f"❌{batsu}/{total}"
    else:
        progress = f"⭕{maru}/{total}"
    
    label = f"{lesson['lesson_title']} (p{lesson['page']}) 【{progress}】"
    lesson_options.append((lesson['lesson_key'], label))

if not lesson_options:
    st.info("この章に学習記録がまだありません")
    st.stop()

selected_lesson_key, selected_label = st.selectbox(
    "単元を選択",
    lesson_options,
    format_func=lambda x: x[1],
    key="retest_lesson_social"
)

# ========== ③ 未解決問題を表示 + 再TEST開始
questions = log.get_questions_in_lesson(selected_lesson_key, filter_batsu_only=True)

if not questions:
    st.success("✅ この単元は完璧です！次の単元に進みましょう")
    st.stop()

col1, col2 = st.columns([2, 1])
with col1:
    st.info(f"**未解決: {len(questions)} 問**")
with col2:
    if st.button("▶️ 再TESTを開始", use_container_width=True, key="retest_start_social"):
        st.session_state.retest_questions_social = questions
        st.session_state.retest_current_index_social = 0
        st.rerun()

# ========== ④ 再TEST中の問題表示（フラッシュカード）
if "retest_questions_social" in st.session_state:
    questions = st.session_state.retest_questions_social
    current_idx = st.session_state.retest_current_index_social
    
    if current_idx >= len(questions):
        st.success(f"✅ {len(questions)}問 再TEST完了！")
        
        if st.button("🏠 セクションに戻る"):
            st.session_state.retest_questions_social = None
            st.rerun()
    else:
        q = questions[current_idx]
        
        st.divider()
        
        # 進捗表示
        st.caption(f"問題 {current_idx + 1}/{len(questions)}")
        
        # 問題表示
        st.markdown(f"**p{q['page']} [{q['section_code']}] {q['q_label']}**")
        st.markdown(f"### {q['answer']}")
        
        # 履歴（直近3回）
        if q['history']:
            history_text = " → ".join(
                ["✅" if r == "maru" else "❌" for r in q['history'][-3:]]
            )
            st.caption(f"直近の結果: {history_text}  |  誤答回数: {q['error_count']}")
        
        # ナビボタン
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("◀", use_container_width=True, disabled=(current_idx == 0), key=f"prev_{current_idx}"):
                st.session_state.retest_current_index_social -= 1
                st.rerun()
        
        with col2:
            if st.button("✅", use_container_width=True, key=f"maru_{current_idx}"):
                st.session_state.retest_current_index_social += 1
                st.rerun()
        
        with col3:
            if st.button("❌", use_container_width=True, key=f"batsu_{current_idx}"):
                st.session_state.retest_current_index_social += 1
                st.rerun()
        
        with col4:
            if st.button("💡", use_container_width=True, key=f"hint_{current_idx}"):
                st.info("※ 教科書を参照してください")
        
        with col5:
            if st.button("▶", use_container_width=True, key=f"next_{current_idx}"):
                st.session_state.retest_current_index_social += 1
                st.rerun()
