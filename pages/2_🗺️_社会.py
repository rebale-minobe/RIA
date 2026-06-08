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

# ========== 再TEST が開始されていない場合のUI
if "retest_started_social" not in st.session_state:
    st.session_state.retest_started_social = False

if not st.session_state.retest_started_social:
    # ===== タイトルを直接選択（workbook_ref 付き）
    st.markdown("### 📖 タイトルを選択")
    
    # すべての章から lesson を抽出
    all_lessons = []
    for chapter_title, _ in log.get_chapters():
        lessons = log.get_lessons_in_chapter(chapter_title)
        all_lessons.extend(lessons)
    
    if not all_lessons:
        st.info("学習記録がまだありません")
        st.stop()
    
    # lesson をボタンとして表示
    for lesson in all_lessons:
        total = lesson['total_count']
        maru = lesson['maru_count']
        batsu = lesson['batsu_count']
        
        if batsu > 0:
            progress = f"❌ {batsu}/{total}"
            badge = "🔴"
        else:
            progress = f"⭕ {maru}/{total}"
            badge = "🟢"
        
        # workbook_ref を取得
        questions = log.get_questions_in_lesson(lesson['lesson_key'], filter_batsu_only=False)
        workbook_ref = ""
        if questions and 'workbook_ref' in questions[0]:
            workbook_ref = questions[0]['workbook_ref']
        
        # ボタンラベル：badge + lesson_title + workbook_ref + progress
        if workbook_ref:
            label = f"{badge} {lesson['lesson_title']} {workbook_ref} 【{progress}】"
        else:
            label = f"{badge} {lesson['lesson_title']} 【{progress}】"
        
        if st.button(
            label,
            key=f"lesson_{lesson['lesson_key']}",
            use_container_width=True
        ):
            st.session_state.selected_lesson_social = lesson['lesson_key']
            st.session_state.retest_questions_social = log.get_questions_in_lesson(
                lesson['lesson_key'],
                filter_batsu_only=True
            )
            st.session_state.retest_current_index_social = 0
            st.session_state.retest_started_social = True
            st.rerun()

# ========== 再TEST が開始されている場合のUI（フラッシュカード）
else:
    if "retest_questions_social" not in st.session_state:
        st.error("エラーが発生しました。最初から選択し直してください。")
        if st.button("🔄 リセット"):
            st.session_state.retest_started_social = False
            st.session_state.pop("selected_lesson_social", None)
            st.session_state.pop("retest_questions_social", None)
            st.rerun()
        st.stop()
    
    questions = st.session_state.retest_questions_social
    current_idx = st.session_state.retest_current_index_social
    
    if current_idx >= len(questions):
        # ===== 完了画面
        st.success(f"✅ {len(questions)}問 再TEST完了！")
        st.balloons()
        
        if st.button("🏠 最初に戻る", use_container_width=True):
            st.session_state.retest_started_social = False
            st.session_state.pop("selected_lesson_social", None)
            st.session_state.pop("retest_questions_social", None)
            st.rerun()
    
    else:
        q = questions[current_idx]
        
        # ===== ヘッダー
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.markdown(f"### 🎯 {current_idx + 1} / {len(questions)}")
        with col2:
            progress_pct = int(100 * (current_idx + 1) / len(questions))
            st.progress(progress_pct / 100, f"{progress_pct}%")
        with col3:
            score = sum(1 for qq in questions[:current_idx] 
                       if qq.get('latest_result') == 'maru')
            st.markdown(f"**⭕ {score}**")
        
        st.divider()
        
        # ===== 問題表示
        st.markdown(f"**p{q['page']} [{q['section_code']}] {q['q_label']}**")
        
        # 問題の答えを大きく表示（フラッシュカード風）
        with st.container(border=True):
            st.markdown(f"# {q['answer']}")
        
        # 履歴情報
        if q['history']:
            history_text = " → ".join(
                ["✅" if r == "maru" else "❌" for r in q['history'][-5:]]
            )
            st.caption(f"直近の結果: {history_text}  |  誤答回数: {q['error_count']}")
        
        st.divider()
        
        # ===== ナビボタン
        col1, col2, col3, col4, col5 = st.columns(5, gap="small")
        
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
