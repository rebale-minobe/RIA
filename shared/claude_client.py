"""
Claude API クライアントラッパー
- vision (画像入力) 対応
- ストリーミング応答対応
- secrets経由でAPIキーを取得
"""
import base64
import streamlit as st
from anthropic import Anthropic

# 現行Sonnet (2026年6月時点)。Anthropicコンソールで利用可能なモデルIDに合わせてください。
MODEL = "claude-sonnet-4-6"


def get_client():
    """Anthropic クライアントを取得"""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error(
            "ANTHROPIC_API_KEY が設定されていません。\n"
            "Streamlit Cloud → Settings → Secrets で登録してください。"
        )
        st.stop()
    return Anthropic(api_key=api_key)


def encode_image(uploaded_file) -> str:
    """Streamlit UploadedFile を base64 文字列に変換"""
    uploaded_file.seek(0)
    return base64.standard_b64encode(uploaded_file.read()).decode("utf-8")


def build_user_content(text: str, images=None) -> list:
    """Claude の user content ブロックを構築"""
    content = []
    if images:
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.type or "image/jpeg",
                    "data": encode_image(img),
                },
            })
    content.append({"type": "text", "text": text})
    return content


def stream_chat(system: str, messages: list, model: str = MODEL, max_tokens: int = 2048):
    """
    ストリーミング応答ジェネレータ。
    messages は [{"role": "user"/"assistant", "content": str or list}, ...]
    """
    client = get_client()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
