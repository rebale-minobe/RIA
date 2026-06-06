"""
数学ページに統合する Study Agent UI コンポーネント
配置先: shared/math_study_agent_ui.py

shared/ui.py の render_subject_page() 内、_render_workbook_answers() の直後で
  if subject_key == "math":
      from shared.math_study_agent_ui import render_study_agent_section
      render_study_agent_section()
として呼び出す
"""

import json
from datetime import datetime, timezone, timedelta

import streamlit as st

# プロジェクト共通モジュールを再利用
from shared.claude_client import encode_image
from modules.study_agent import (
    extract_problem_from_image,
    generate_practice_problems,
    generate_explanation,
)

_JST = timezone(timedelta(hours=9))
def _now_jst():
    return datetime.now(_JST).replace(tzinfo=None)


def render_study_agent_section():
    """数学ページの Study Agent セクション"""

    st.markdown("---")
    st.markdown("## 🤖 Study Agent — AIが類題を自動生成")
    st.caption("解けなかった問題をアップロードすると、AIが難易度別の類題3問を作ります")

    with st.expander("📷 問題から類題をつくる", expanded=False):

        # ── Step 1: 問題の入力 ──
        st.markdown("**Step 1: 問題を入力**")

        input_method = st.radio(
            "入力方法",
            ["📸 スクショをアップロード", "✏️ 問題文を手入力"],
            horizontal=True,
            key="sa_input_method",
            label_visibility="collapsed",
        )

        if input_method == "📸 スクショをアップロード":
            uploaded = st.file_uploader(
                "ワークのスクショ",
                type=["jpg", "jpeg", "png"],
                key="sa_uploader",
                label_visibility="collapsed",
            )
            if uploaded:
                st.image(uploaded, caption="アップロード済み", use_container_width=True)
                if st.button("🔍 画像から問題を抽出", use_container_width=True, type="primary", key="sa_extract"):
                    with st.spinner("Claudeが画像を読み取り中…"):
                        img_b64 = encode_image(uploaded)
                        media_type = uploaded.type or "image/jpeg"
                        result = extract_problem_from_image(img_b64, media_type)
                        if result.get("success"):
                            st.session_state.sa_problem = result["problem_text"]
                            st.session_state.sa_chapter = result.get("chapter", "")
                            st.success("✅ 問題を抽出しました")
                        else:
                            st.error("問題が読み取れませんでした。手入力に切り替えてください。")

        else:  # 手入力
            txt = st.text_area(
                "問題文（例：次の式を計算しなさい 2(3x-1)+5(x+2)）",
                height=100,
                key="sa_manual_text",
                label_visibility="collapsed",
            )
            chap = st.text_input(
                "章（例：2年-第1章-式の計算）",
                key="sa_manual_chapter",
                label_visibility="collapsed",
                placeholder="章（任意）",
            )
            if txt:
                st.session_state.sa_problem = txt
                st.session_state.sa_chapter = chap

        # ── Step 2: 類題生成 ──
        if st.session_state.get("sa_problem"):
            st.markdown("---")
            st.markdown("**抽出された問題**")
            st.info(st.session_state.sa_problem)
            if st.session_state.get("sa_chapter"):
                st.caption(f"📚 {st.session_state.sa_chapter}")

            st.markdown("**Step 2: 類題を生成**")
            if st.button("✨ 基本・標準・応用の3問を生成", use_container_width=True, type="primary", key="sa_generate"):
                with st.spinner("Claudeが類題を作成中…"):
                    problems = generate_practice_problems(
                        st.session_state.sa_problem,
                        st.session_state.get("sa_chapter", ""),
                    )
                    if problems:
                        st.session_state.sa_generated = problems
                        st.session_state.sa_timestamp = _now_jst().isoformat()
                        st.success("✅ 類題を生成しました")
                    else:
                        st.error("生成に失敗しました。もう一度お試しください。")

        # ── Step 3: 生成された問題を1問ずつ表示 ──
        if st.session_state.get("sa_generated"):
            st.markdown("---")
            st.markdown("### ✨ 生成された類題")

            for i, prob in enumerate(st.session_state.sa_generated, 1):
                with st.container(border=True):
                    st.markdown(f"**問題 {i}　[{prob.get('difficulty', '')}]**")
                    st.markdown(prob.get("problem", ""))

                    with st.expander("💡 ヒント"):
                        st.write(prob.get("hint", ""))

                    with st.expander("📖 解き方（ステップ）"):
                        for j, step in enumerate(prob.get("solution_steps", []), 1):
                            st.write(f"{j}. {step}")

                    with st.expander("✅ 答え"):
                        st.code(prob.get("full_solution", ""))

                    if st.button("📚 詳しい解説を見る", key=f"sa_explain_{prob.get('id', i)}", use_container_width=True):
                        with st.spinner("解説を作成中…"):
                            explanation = generate_explanation(prob.get("problem", ""))
                            st.info(explanation)
