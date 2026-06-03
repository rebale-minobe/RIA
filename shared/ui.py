"""共通UIコンポーネント・教科ページ共通テンプレート"""
import streamlit as st
from shared.claude_client import stream_chat, build_user_content
from shared.profile import get_profile
from modules.schedule.manager import get_subject_range


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

    # ─── 操作ボタン ───
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 会話をクリア", key=f"clear_{subject_key}"):
            st.session_state[session_key] = []
            st.rerun()

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

    # ─── 写真アップローダー ───
    uploaded_files = st.file_uploader(
        "📷 教材・ワーク・プリントの写真をアップロード",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"uploader_{subject_key}",
    )

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
