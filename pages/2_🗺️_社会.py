"""社会ページ v3 - AI 4択問題 + TOP同等UIデザイン対応"""
import streamlit as st
import json
from shared.ui import render_subject_page
from shared.answer_log_hierarchy import AnswerLogPivot
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="社会 - RIA", page_icon="🗺️", layout="wide")
render_subject_page("social", "社会", "🗺️")

# ========== JST ヘルパー
_JST = timezone(timedelta(hours=9))
def _now_jst():
    return datetime.now(_JST).replace(tzinfo=None)

# ========== TOP 同等のUI スタイル
st.markdown("""
<style>
    /* 4択選択肢のデザイン */
    .choice-button {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        border-radius: 12px;
        border: 2px solid #E5E5EA;
        background: white;
        color: #1c1c1e;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.2s ease;
        min-height: 60px;
        text-align: center;
        line-height: 1.4;
    }
    .choice-button:hover {
        border-color: #007AFF;
        background: #F0F7FF;
    }
    
    /* 正解ボタン */
    .choice-correct {
        border-color: #34C759;
        background: #E8F8EE;
        color: #34C759;
    }
    
    /* 不正解ボタン */
    .choice-incorrect {
        border-color: #FF3B30;
        background: #FFE8E6;
        color: #FF3B30;
    }
    
    /* 問題文コンテナ */
    .question-container {
        background: white;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        border-left: 4px solid #FF9500;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .question-text {
        font-size: 18px;
        font-weight: 600;
        color: #1c1c1e;
        line-height: 1.6;
        margin: 0;
    }
    
    .question-meta {
        font-size: 13px;
        color: #8E8E93;
        margin-top: 8px;
        font-weight: 500;
    }
    
    /* タイトルセクション */
    .title-section {
        background: linear-gradient(135deg, #FF9500 0%, #FFB84D 100%);
        color: white;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(255, 149, 0, 0.2);
    }
    
    .title-section h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    
    .title-section p {
        margin: 4px 0 0 0;
        font-size: 13px;
        opacity: 0.9;
    }
    
    /* ナビゲーションボタン */
    .nav-button {
        min-height: 44px;
        font-weight: 600;
        border-radius: 10px;
        font-size: 14px;
        letter-spacing: -0.01em;
    }
</style>
""", unsafe_allow_html=True)

# ========== ワーク再TEST セクション
st.markdown("---")
st.subheader("🔄 ワーク再TEST")
st.caption("最近の誤答問題を4択で復習")

# キャッシュで CSV を読み込み
@st.cache_data(ttl=86400)
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

# ========== AI 4択問題生成関数
def _generate_quiz(q_data: dict) -> dict | None:
    """AI に4択問題を生成させる"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))
        lesson  = q_data.get("lesson_title", "")
        answer  = q_data.get("answer", "")
        subject = "社会"
        genre   = "歴史"
        
        prompt = (
            f"中学2年生の{subject}（{genre}）の単元「{lesson}」に関する問題を1問作ってください。\n"
            f"正解は「{answer}」です。\n\n"
            f"【ルール】\n"
            f"- 必ずこの単元・テーマの文脈で出題する（他の単元の知識は不要）\n"
            f"- 問題文は1文で、明確に問う\n"
            f"- 選択肢は4つ（正解1つ＋ダミー3つ）\n"
            f"- ダミーはこの単元に登場する似た語句・人物・地名から選ぶ\n"
            f"- 各選択肢には読み仮名（ふりがな・ひらがな）を必ず付ける\n"
            f"  （カタカナ語はカタカナのままでよい。記号や数字だけの場合は空文字）\n"
            f"- JSONのみ出力（説明不要）\n\n"
            f"出力フォーマット:\n"
            f'{{\n'
            f'  "question": "問題文",\n'
            f'  "choices": [\n'
            f'    {{"text": "選択肢A", "yomi": "せんたくしえー"}},\n'
            f'    {{"text": "選択肢B", "yomi": "せんたくしびー"}},\n'
            f'    {{"text": "選択肢C", "yomi": "せんたくししー"}},\n'
            f'    {{"text": "選択肢D", "yomi": "せんたくしでぃー"}}\n'
            f'  ],\n'
            f'  "answer": "正解の選択肢テキスト（いずれかのtextと完全一致）"\n'
            f'}}'
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=800,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "中学生向けに問題を作る先生です。必ずJSONで返答してください。"},
                {"role": "user", "content": prompt},
            ]
        )
        data = json.loads(resp.choices[0].message.content)
        
        # choices正規化
        _norm = []
        for c in data.get("choices", []):
            if isinstance(c, dict):
                _norm.append({"text": str(c.get("text", "")), "yomi": str(c.get("yomi", "") or "")})
            else:
                _norm.append({"text": str(c), "yomi": ""})
        data["choices"] = _norm
        
        # choicesをシャッフル
        import random as _rnd
        _rnd.shuffle(data["choices"])
        return data
    except Exception as e:
        st.error(f"❌ AI問題生成エラー: {e}")
        return None

# ========== UI 状態管理
if "retest_started_social" not in st.session_state:
    st.session_state.retest_started_social = False

if not st.session_state.retest_started_social:
    # ===== タイトル選択画面
    st.markdown("### 📖 タイトルを選択")
    
    all_lessons = []
    for chapter_title, _ in log.get_chapters():
        lessons = log.get_lessons_in_chapter(chapter_title)
        all_lessons.extend(lessons)
    
    if not all_lessons:
        st.info("学習記録がまだありません")
        st.stop()
    
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
        
        questions = log.get_questions_in_lesson(lesson['lesson_key'], filter_batsu_only=False)
        workbook_ref = ""
        if questions and 'workbook_ref' in questions[0]:
            workbook_ref = questions[0]['workbook_ref']
        
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
            st.session_state.selected_lesson_title = lesson['lesson_title']
            st.session_state.retest_questions_social = log.get_questions_in_lesson(
                lesson['lesson_key'],
                filter_batsu_only=True
            )
            st.session_state.retest_current_index_social = 0
            st.session_state.retest_started_social = True
            st.rerun()

# ========== 再TEST が開始されている場合（AI 4択問題）
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
    lesson_title = st.session_state.get("selected_lesson_title", "")
    
    if current_idx >= len(questions):
        # ===== 完了画面
        st.success(f"✅ {len(questions)}問 再TEST完了！🎉")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 タイトル一覧に戻る", use_container_width=True):
                st.session_state.retest_started_social = False
                st.session_state.pop("selected_lesson_social", None)
                st.session_state.pop("retest_questions_social", None)
                st.rerun()
    
    else:
        q = questions[current_idx]
        
        # ===== タイトルセクション（TOP同等デザイン）
        st.markdown(f"""
        <div class='title-section'>
            <h3>📖 {lesson_title}</h3>
            <p>問題 {current_idx + 1} / {len(questions)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ===== 進捗バーと正解数
        col1, col2, col3 = st.columns([1, 2, 1], gap="small")
        with col1:
            st.markdown("**進捗**")
        with col2:
            progress_pct = int(100 * (current_idx + 1) / len(questions))
            st.progress(progress_pct / 100, f"{progress_pct}%")
        with col3:
            score = sum(1 for i in range(current_idx) 
                       if st.session_state.get(f"social_result_{i}", "") == "maru")
            st.markdown(f"**⭕ {score}**")
        
        st.divider()
        
        # ===== 問題データを整形
        quiz_data = {
            "lesson_title": q.get('lesson_title', ''),
            "answer": q.get('answer', ''),
            "page_number": q.get('page', ''),
            "section_code": q.get('section_code', ''),
            "q": q.get('q_label', ''),
        }
        
        # ===== AI クイズ生成（キャッシュ）
        quiz_key = f"social_quiz_{current_idx}_{q.get('q_label','')}"
        if quiz_key not in st.session_state:
            with st.spinner("AI が問題を生成中..."):
                quiz = _generate_quiz(quiz_data)
                st.session_state[quiz_key] = quiz
        quiz = st.session_state.get(quiz_key)
        
        if quiz is None:
            st.warning("⚠️ 問題生成に失敗しました。スキップします。")
            if st.button("次へ", use_container_width=True):
                st.session_state.retest_current_index_social += 1
                st.rerun()
        else:
            # ===== 問題表示（TOP同等デザイン）
            st.markdown(f"""
            <div class='question-container'>
                <p class='question-text'>{quiz['question']}</p>
                <p class='question-meta'>p{q['page']} [{q['section_code']}]</p>
            </div>
            """, unsafe_allow_html=True)
            
            # ===== 選択肢ボタン（2列×2行）
            cols = st.columns(2, gap="medium")
            for i, choice in enumerate(quiz['choices']):
                col_idx = i % 2
                with cols[col_idx]:
                    choice_text = choice.get('text', '')
                    choice_yomi = choice.get('yomi', '')
                    
                    display_label = f"{choice_text}\n（{choice_yomi}）" if choice_yomi else choice_text
                    
                    if st.button(
                        display_label,
                        key=f"social_choice_{current_idx}_{i}",
                        use_container_width=True,
                    ):
                        is_correct = choice_text == quiz['answer']
                        st.session_state[f"social_result_{current_idx}"] = "maru" if is_correct else "batsu"
                        
                        if is_correct:
                            st.success("✅ 正解！")
                        else:
                            st.error(f"❌ 不正解\n正解：**{quiz['answer']}**")
                        
                        st.session_state.retest_current_index_social += 1
                        import time
                        time.sleep(1.5)
                        st.rerun()
            
            st.divider()
            
            # ===== ナビゲーション
            nav_cols = st.columns([1, 1, 1, 1, 1], gap="small")
            
            with nav_cols[0]:
                if st.button("◀ 前へ", use_container_width=True, disabled=(current_idx == 0), key=f"prev_{current_idx}"):
                    st.session_state.retest_current_index_social -= 1
                    st.rerun()
            
            with nav_cols[1]:
                if st.button("↩️ 戻る", use_container_width=True, key=f"back_{current_idx}"):
                    st.session_state.retest_started_social = False
                    st.session_state.pop("selected_lesson_social", None)
                    st.session_state.pop("retest_questions_social", None)
                    st.rerun()
            
            with nav_cols[2]:
                if st.button("💡", use_container_width=True, key=f"hint_{current_idx}"):
                    st.info(f"**ヒント：答えは「{q.get('answer', '？')}」です**")
            
            with nav_cols[3]:
                st.empty()
            
            with nav_cols[4]:
                if st.button("次へ ▶", use_container_width=True, key=f"next_{current_idx}"):
                    st.session_state.retest_current_index_social += 1
                    st.rerun()

# ========== 教材・ワーク・プリントのアップロード
st.markdown("---")
st.subheader("📸 教材・ワーク・プリントの写真をアップロード")
st.caption("解答用紙やプリントの写真をアップロードして、AI で分析できるようにします")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_image = st.file_uploader(
        "写真をアップロード（JPG, PNG）",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )
with col2:
    upload_button = st.button("📤 アップロード", use_container_width=True)

if uploaded_image and upload_button:
    st.info("✅ アップロード機能は今後実装予定です")

