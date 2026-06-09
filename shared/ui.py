"""共通UIコンポーネント・教科ページ共通テンプレート"""
import json
from pathlib import Path
import streamlit as st
from shared.claude_client import stream_chat, build_user_content
from shared.profile import get_profile
from modules.schedule.manager import get_subject_range


# ジャンル英 → 日本語名マッピング（ワーク解答表示用）
_GENRE_JP = {
    "history": "歴史", "geography": "地理", "civics": "公民",
    "reading": "読解", "classic": "古文・漢文",
    "kanji": "漢字・語彙", "grammar": "文法",
    "field1": "第1分野", "field2": "第2分野",
    "general": "",
}


# 教科キー → プロンプトモジュール のマッピング
def _get_prompt_module(subject_key: str):
    """教科別のシステムプロンプトを返す"""
    if subject_key == "japanese":
        from modules.japanese import prompts
    elif subject_key == "social":
        from modules.social import prompts
    elif subject_key == "math":
        from modules.math import prompts
    elif subject_key == "science":
        from modules.science import prompts
    elif subject_key == "english":
        from modules.english import prompts
    else:
        return None
    return prompts


def _render_workbook_answers(subject_key: str):
    """data/{subject_key}_*_workbook_answers.json があれば expander 内に表示"""
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        return

    answer_files = sorted(data_dir.glob(f"{subject_key}_*_workbook_answers.json"))
    if not answer_files:
        return

    with st.expander("📝 ワーク解答", expanded=False):
        # ジャンル選択（複数あれば）
        if len(answer_files) > 1:
            options = {}
            for f in answer_files:
                stem = f.stem  # e.g. social_history_workbook_answers
                genre_key = stem.replace(f"{subject_key}_", "").replace("_workbook_answers", "")
                jp = _GENRE_JP.get(genre_key, genre_key) or genre_key
                options[jp] = f
            sel = st.radio(
                "ジャンル", list(options.keys()),
                horizontal=True,
                key=f"wb_genre_{subject_key}",
                label_visibility="collapsed",
            )
            chosen = options[sel]
        else:
            chosen = answer_files[0]

        try:
            with open(chosen, "r", encoding="utf-8") as f:
                wb = json.load(f)
        except Exception as e:
            st.error(f"解答データ読み込みエラー: {e}")
            return

        if not wb.get("pages"):
            st.info("解答データが空です")
            return

        # ページ選択
        page_options = [
            f"P.{p['page_number']}　{p['lesson_title']}"
            for p in wb["pages"]
        ]
        sel_page_label = st.selectbox(
            "ページ", page_options,
            key=f"wb_page_{subject_key}",
            label_visibility="collapsed",
        )
        page = wb["pages"][page_options.index(sel_page_label)]

        # ヘッダー情報
        meta_parts = []
        chap = f"{page.get('chapter_number','') or ''} {page.get('chapter_title','') or ''}".strip()
        if chap:
            meta_parts.append(f"📖 {chap}")
        if page.get("question_pages_ref"):
            meta_parts.append(f"参照: {page['question_pages_ref']}")
        if meta_parts:
            st.caption("　/　".join(meta_parts))

        # セクション
        for section in page["sections"]:
            sec_label = f"**{section['code']}**　{section['name']}"
            if section.get("textbook_ref"):
                sec_label += f"　— {section['textbook_ref']}"
            st.markdown(sec_label)
            if section.get("subtitle"):
                st.caption(section["subtitle"])

            for group in section["groups"]:
                if group.get("label"):
                    st.markdown(f"　**{group['label']}**")
                for ans in group["answers"]:
                    note = f" *※{ans['note']}*" if ans.get("note") else ""
                    # CSV登録ボタン（socialのみ）
                    if subject_key == "social":
                        col_q, col_o, col_x = st.columns([6, 1, 1])
                        col_q.markdown(f"　`{ans['q']}` {ans['a']}{note}")
                        if ans.get("context"):
                            col_q.caption(f"　　💭 {ans['context']}")
                        q_data = {
                            "page_num": str(page.get("page_number", "")),
                            "section_code": section.get("code", ""),
                            "q_label": ans.get("q", ""),
                            "answer": ans.get("a", ""),
                        }
                        btn_o = f"wb_csv_o_{subject_key}_{page.get('page_number','')}_{section.get('code','')}_{ans.get('q','')}"
                        btn_x = f"wb_csv_x_{subject_key}_{page.get('page_number','')}_{section.get('code','')}_{ans.get('q','')}"
                        if col_o.button("⭕", key=btn_o, use_container_width=True):
                            try:
                                from modules import answer_log_pivot as _alp
                                ok = _alp.append_pivot_log(subject_key, q_data, "maru")
                                st.toast("⭕ 登録完了" if ok else "❌ 登録失敗")
                            except Exception as e:
                                st.toast(f"エラー: {e}")
                        if col_x.button("❌", key=btn_x, use_container_width=True):
                            try:
                                from modules import answer_log_pivot as _alp
                                ok = _alp.append_pivot_log(subject_key, q_data, "batsu")
                                st.toast("❌ 登録完了" if ok else "登録失敗")
                            except Exception as e:
                                st.toast(f"エラー: {e}")
                    else:
                        st.markdown(f"　`{ans['q']}` {ans['a']}{note}")
                        if ans.get("context"):
                            st.caption(f"　　💭 {ans['context']}")
            st.markdown("")


def render_subject_page(subject_key: str, subject_name: str, icon: str):
    """各教科ページの共通レンダリング"""

    st.title(f"{icon} {subject_name}")

    # ─── 試験範囲表示 ───
    range_info = get_subject_range(subject_key)
    if range_info:
        label = f"📋 期末範囲（{range_info.get('date', '')} {range_info.get('period', '')}校時 {range_info.get('time', '')}）"
        with st.expander(label, expanded=False):
            st.markdown(f"**範囲:** {range_info.get('range', '範囲情報なし')}")
            if range_info.get('points'):
                st.markdown(f"**学習のポイント:** {range_info['points']}")
            if range_info.get('submission'):
                st.markdown(f"**提出物:** {range_info['submission']}")

    # ─── 教科書/ワーク（TOP同等・共通コア） ───
    st.markdown("---")
    st.markdown(
        '<div style="font-size:22px;font-weight:700;margin:8px 0 4px;">📚 教科書/ワーク</div>',
        unsafe_allow_html=True
    )
    from shared.study_core import render_subject_study
    render_subject_study(subject_key)

    # ─── Study Agent（数学のみ・AI類題生成） ───
    if subject_key == "math":
        from shared.math_study_agent_ui import render_study_agent_section
        render_study_agent_section()

    # ─── 漢字テスト（国語のみ） ───
    if subject_key == "japanese":
        st.markdown("---")
        st.markdown(
            '<div style="font-size:22px;font-weight:700;margin:8px 0 4px;">📖 漢字テスト</div>',
            unsafe_allow_html=True
        )
        from shared.kanji_test import render_kanji_test
        render_kanji_test()

    # ─── システムプロンプト構築 ───
    module = _get_prompt_module(subject_key)
    if module is None:
        st.error(f"教科 '{subject_key}' のプロンプトモジュールが見つかりません")
        return

    profile = get_profile()
    range_text = ""
    if range_info:
        range_text = f"{range_info.get('range', '')}\n\nポイント: {range_info.get('points', '')}"

    system_prompt = module.SYSTEM_PROMPT.format(
        profile=profile.get_summary_text(),
        range_info=range_text or "範囲情報なし",
    )

    # ─── セッションステート初期化 ───
    session_key = f"messages_{subject_key}"
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    # ─── 操作ボタン（非表示）───
    # 会話クリアは不要のため非表示

    # ─── 会話履歴表示 ───
    for msg in st.session_state[session_key]:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, str):
                st.markdown(content)
            else:
                # マルチモーダル content (画像+テキスト)
                has_image = False
                text_parts = []
                for block in content:
                    if block["type"] == "text":
                        text_parts.append(block["text"])
                    elif block["type"] == "image":
                        has_image = True
                if has_image:
                    st.caption("📷 画像を共有しました")
                if text_parts:
                    st.markdown("\n".join(text_parts))

    # ─── 写真アップローダー（非表示）───
    # 教科書・ワーク登録は教科書管理ページで行うため非表示
    uploaded_files = []

    # ─── チャット入力 ───
    user_input = st.chat_input(f"{subject_name}について質問する…")

    if user_input:
        user_content = build_user_content(user_input, uploaded_files)
        st.session_state[session_key].append({"role": "user", "content": user_content})

        with st.chat_message("user"):
            if uploaded_files:
                st.caption(f"📷 {len(uploaded_files)}枚の画像を添付")
            st.markdown(user_input)

        with st.chat_message("assistant"):
            try:
                response_text = st.write_stream(
                    stream_chat(system_prompt, st.session_state[session_key])
                )
                st.session_state[session_key].append(
                    {"role": "assistant", "content": response_text}
                )
            except Exception as e:
                st.error(f"Claude API エラー: {e}")
                # 失敗したらユーザーメッセージを履歴から戻す
                st.session_state[session_key].pop()
