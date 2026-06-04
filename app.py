"""
RIA TOP ページ v1.4
v1.4 追加:
- 解答ログの永続化（data/answer_log.json）
- 「📌 今日の問題」セクション: 過去に間違えた問題を教科横断で反復出題
- ○✕記録は即座に GitHub に保存
v1.3 追加: フラッシュカード形式、◀▶ナビ、○✕記録、💡解説、再テスト
"""

import streamlit as st
import json
import requests
import base64
import random
from datetime import datetime
from pathlib import Path

# 解答ログ管理（GitHub 永続化）
try:
    from modules import answer_log
    ANSWER_LOG_AVAILABLE = True
except Exception:
    ANSWER_LOG_AVAILABLE = False

st.set_page_config(page_title="RIA", page_icon="🌟", layout="wide", initial_sidebar_state="collapsed")

SUBJECT_COLOR_MAP = {
    "国語":     {"primary": "#FF2D55", "light": "#FFE5EC", "emoji": "📘"},
    "数学":     {"primary": "#007AFF", "light": "#E5F1FF", "emoji": "📐"},
    "社会":     {"primary": "#FF9500", "light": "#FFF4E5", "emoji": "🗺️"},
    "理科":     {"primary": "#34C759", "light": "#E8F8EE", "emoji": "🔬"},
    "英語":     {"primary": "#AF52DE", "light": "#F5EBFB", "emoji": "🌐"},
    "保健体育": {"primary": "#FF3B30", "light": "#FFE8E6", "emoji": "🏃"},
    "技術家庭": {"primary": "#5AC8FA", "light": "#E8F7FE", "emoji": "🔧"},
    "技術":     {"primary": "#5AC8FA", "light": "#E8F7FE", "emoji": "🔧"},
    "家庭":     {"primary": "#5AC8FA", "light": "#E8F7FE", "emoji": "🍳"},
    "音楽":     {"primary": "#FFCC00", "light": "#FFF8D6", "emoji": "🎵"},
    "美術":     {"primary": "#FF6482", "light": "#FFE5EB", "emoji": "🎨"},
}

def subject_color(name):
    name = str(name).strip()
    for key, val in SUBJECT_COLOR_MAP.items():
        if key in name:
            return val
    return {"primary": "#8E8E93", "light": "#F2F2F7", "emoji": "📚"}


# ===== スタイル =====
st.markdown("""
<style>
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                     "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background: #fafafa;
    }

    .section-title {
        font-size: 24px; font-weight: 700;
        margin: 28px 0 12px 0;
        color: #1c1c1e; letter-spacing: -0.01em;
    }

    .test-card {
        background: linear-gradient(135deg, #FF3B30 0%, #FF2D55 100%);
        color: white; border-radius: 16px; padding: 24px 20px; text-align: center;
        box-shadow: 0 4px 16px rgba(255, 59, 48, 0.2);
    }

    .range-item {
        background: white; padding: 14px 16px; border-radius: 12px;
        border-left: 4px solid #FF3B30; margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .study-time-badge {
        color: white; padding: 3px 10px; border-radius: 10px;
        font-size: 13px; font-weight: 600;
    }
    .cover-ph {
        background: linear-gradient(135deg, #e0e0e0, #c0c0c0); height: 180px;
        border-radius: 12px; display: flex; align-items: center; justify-content: center;
        color: #888; font-size: 13px; padding: 8px; text-align: center;
    }
    .now-badge {
        text-align: right; color: #8E8E93; font-size: 13px;
        margin: -10px 0 10px 0; font-weight: 500;
    }

    /* カレンダー */
    .calendar-scroll {
        display: flex; gap: 8px;
        overflow-x: auto; padding: 20px 4px 12px;
        -webkit-overflow-scrolling: touch;
        scroll-snap-type: x mandatory;
    }
    .calendar-scroll::-webkit-scrollbar { height: 6px; }
    .calendar-scroll::-webkit-scrollbar-thumb { background: #d1d1d6; border-radius: 3px; }
    .day-card {
        flex-shrink: 0; width: 86px; min-height: 128px;
        background: white; border-radius: 12px; padding: 10px 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.05);
        scroll-snap-align: start; position: relative;
    }
    .day-card.today {
        border-color: #007AFF; border-width: 2px;
        background: linear-gradient(135deg, #E5F1FF 0%, #fff 100%);
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.18);
    }
    .day-card.test-day {
        border-color: #FF3B30; border-width: 2px;
        background: linear-gradient(135deg, #FFE5E2 0%, #fff 100%);
        box-shadow: 0 4px 12px rgba(255, 59, 48, 0.15);
    }
    .day-card.past { opacity: 0.4; }
    .today-badge {
        position: absolute; top: -12px; left: 50%;
        transform: translateX(-50%);
        background: #007AFF; color: white;
        font-size: 10px; font-weight: 700;
        padding: 3px 9px; border-radius: 10px;
        white-space: nowrap; letter-spacing: 0.02em;
        box-shadow: 0 2px 6px rgba(0, 122, 255, 0.35);
    }
    .day-num { font-size: 18px; font-weight: 700; color: #1c1c1e; text-align: center; line-height: 1.1; }
    .day-wd { font-size: 11px; text-align: center; margin-bottom: 6px; font-weight: 500; }
    .chips { display: flex; flex-direction: column; gap: 3px; }
    .chip {
        font-size: 11px; padding: 3px 5px; border-radius: 6px;
        background: #F2F2F7; color: #666; text-align: center;
        font-weight: 600; line-height: 1.3;
    }
    .chip-test {
        background: #FF3B30 !important; color: white !important;
        font-weight: 700; border: none !important;
    }
    .chip-submit {
        background: #FFCC00 !important; color: #5a4a00 !important;
        font-weight: 700; border: none !important;
    }

    /* ToDo カード */
    [class*="st-key-todo_card_"] {
        border-radius: 14px !important;
        padding: 14px !important;
        background: white !important;
        margin: 8px 0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04) !important;
    }
    .todo-subj-header { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
    [class*="st-key-todo_card_"] input[type="text"] {
        font-size: 13px; background: #FAFAFA;
        border: 1px solid #E5E5EA; border-radius: 8px;
    }
    [class*="st-key-todo_card_"] [data-baseweb="select"] { font-size: 13px; }

    /* ポイントボックス */
    .point-box, .point-box-blue {
        padding: 14px 18px; border-radius: 12px;
        margin: 8px 0 14px 0; line-height: 1.8;
    }
    .point-box { background: #FFF8E1; border-left: 3px solid #FFCC00; }
    .point-box-blue { background: #E5F1FF; border-left: 3px solid #007AFF; }
    .point-box p, .point-box-blue p { font-size: 15px; line-height: 1.8; margin: 6px 0; }
    .point-box h1, .point-box-blue h1,
    .point-box h2, .point-box-blue h2 {
        font-size: 19px !important; font-weight: 700;
        margin: 14px 0 6px 0 !important; line-height: 1.4 !important;
    }
    .point-box h3, .point-box-blue h3 {
        font-size: 16px !important; font-weight: 700;
        margin: 12px 0 4px 0 !important;
    }
    .point-box ul, .point-box-blue ul,
    .point-box ol, .point-box-blue ol { padding-left: 22px; margin: 6px 0; }
    .point-box li, .point-box-blue li { font-size: 15px; line-height: 1.8; margin: 3px 0; }

    /* TOC */
    .toc-sect-title {
        font-size: 14px; font-weight: 700;
        color: #1c1c1e; margin: 12px 0 4px 0;
    }
    .toc-sub {
        font-size: 13px; line-height: 1.7;
        padding: 10px 4px 10px 4px;
    }
    .toc-sub .toc-page { color: #8E8E93; font-size: 0.9em; }

    .st-key-tb_toc div[data-testid="stExpander"] summary,
    .st-key-tb_toc div[data-testid="stExpander"] summary p { font-size: 14px !important; }
    .st-key-tb_toc div[data-testid="stExpander"] { margin: 4px 0; border-radius: 10px; }
    .st-key-tb_toc div[data-testid="stHorizontalBlock"] {
        border-bottom: 1px dashed #d8d8d8;
        align-items: center; margin-bottom: 0 !important;
    }
    .st-key-tb_toc div[data-testid="stHorizontalBlock"]:last-child { border-bottom: none; }
    .st-key-tb_toc div[data-testid="stButton"] button {
        min-height: 36px !important; padding: 4px 8px !important; font-size: 16px !important;
    }

    /* ===== ワーク フラッシュカード ===== */
    .wb-detail-title {
        font-size: 20px; font-weight: 700; color: #1c1c1e;
        margin: 8px 0 4px 0;
    }
    .wb-mode-badge {
        display: inline-block; padding: 4px 14px;
        border-radius: 20px; font-size: 12px; font-weight: 700;
        margin: 8px 0 4px 0;
    }
    .wb-mode-retest { background: #FF6B00; color: white; }
    .wb-progress-row {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 14px; font-weight: 600;
        margin: 12px 0 4px 0;
    }
    .wb-progress-row .ans-stat {
        font-size: 13px; padding: 2px 10px;
        border-radius: 12px; margin-left: 6px;
    }

    .wb-flashcard {
        background: white;
        border-radius: 18px;
        padding: 20px 24px 24px 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border: 2px solid #FF9500;
        margin: 12px 0 16px 0;
    }
    .wb-fc-header {
        text-align: center;
        margin-bottom: 10px;
    }
    .wb-fc-meta {
        font-size: 11px;
        color: #8E8E93;
        font-weight: 600;
        letter-spacing: 0.04em;
    }
    .wb-fc-lesson {
        font-size: 14px;
        font-weight: 700;
        color: #1c1c1e;
        margin-top: 2px;
    }
    .wb-fc-q {
        font-size: 32px;
        font-weight: 800;
        color: #FF9500;
        text-align: center;
        line-height: 1.0;
        margin: 10px 0 6px 0;
    }
    .wb-fc-divider {
        border-top: 1px dashed #e5e5ea;
        margin: 14px -10px;
    }
    .wb-fc-a-area {
        text-align: center;
        min-height: 70px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 12px 0;
    }
    .wb-fc-a-shown {
        font-size: 38px;
        font-weight: 700;
        color: #1c1c1e;
        line-height: 1.4;
        max-width: 100%;
        word-break: break-word;
        animation: ansReveal 0.25s ease-out;
    }
    .wb-fc-a-hidden {
        font-size: 56px;
        color: #d1d1d6;
        font-weight: 800;
    }
    @keyframes ansReveal {
        from { opacity: 0; transform: scale(0.95); }
        to   { opacity: 1; transform: scale(1); }
    }
    .wb-result-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 4px;
    }
    .wb-result-badge.maru { background: #E5F1FF; color: #007AFF; }
    .wb-result-badge.batsu { background: #FFE5E2; color: #FF3B30; }

    /* ナビボタン (4列) — Apple HIG風 ワーク詳細＆今日の問題 共通 */

    /* 共通ベース */
    .st-key-wb_nav_row button,
    .st-key-tp_nav_row button {
        font-size: 20px !important;
        min-height: 60px !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 16px !important;
        letter-spacing: 0.01em !important;
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
    }
    .st-key-wb_nav_row button:active,
    .st-key-tp_nav_row button:active {
        transform: scale(0.96) !important;
    }
    .st-key-wb_nav_row button:disabled,
    .st-key-tp_nav_row button:disabled {
        opacity: 0.22 !important;
        box-shadow: none !important;
    }

    /* ◀ 前へ — グレー */
    .st-key-wb_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(1) button,
    .st-key-tp_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background: #E5E5EA !important;
        color: #3a3a3c !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    }

    /* ❌ バツ — 白ベース・赤枠（トグル） */
    .st-key-wb_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(2) button,
    .st-key-tp_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background: white !important;
        color: #FF3B30 !important;
        border: 2px solid #FF3B30 !important;
        box-shadow: 0 2px 8px rgba(255,59,48,0.12) !important;
    }

    /* 💡 解説 — ミントグリーン */
    .st-key-wb_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(3) button,
    .st-key-tp_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(3) button {
        background: #E8F8EE !important;
        color: #1a8a3c !important;
        box-shadow: 0 2px 6px rgba(52,199,89,0.12) !important;
    }

    /* ▶ 次へ — プライマリブルー・主アクション */
    .st-key-wb_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(4) button,
    .st-key-tp_nav_row [data-testid="stHorizontalBlock"] > div:nth-child(4) button {
        background: linear-gradient(160deg, #007AFF 0%, #0055d4 100%) !important;
        color: white !important;
        box-shadow: 0 4px 14px rgba(0,122,255,0.35) !important;
        font-size: 22px !important;
    }

    /* 答えを見るボタン */
    .st-key-wb_reveal_wrap button,
    .st-key-tp_reveal_wrap button {
        background: linear-gradient(135deg, #FF9500, #FF7A00) !important;
        color: white !important;
        font-size: 16px !important;
        min-height: 52px !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(255, 149, 0, 0.35) !important;
    }

    /* カバー */
    .tb-cover-wrap { text-align: center; padding: 16px 0 8px 0; }
    .tb-cover {
        width: 220px; max-width: 70%; border-radius: 12px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.12);
    }
    .st-key-tb_open_btn_wrap, .st-key-wb_open_btn_wrap {
        max-width: 240px !important;
        margin: 4px auto 16px auto !important;
    }

    /* ボタン基本 */
    div.stButton > button {
        min-height: 46px; font-size: 15px;
        border-radius: 12px !important;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); }
    div.stButton > button[kind="primary"] { background: #007AFF; border: none; }
    div.stButton > button[kind="primary"]:hover { background: #0066d6; }

    div[role="radiogroup"] { justify-content: flex-start; }

    div[data-testid="stSegmentedControl"] { display: flex; justify-content: center; }
    div[data-testid="stSegmentedControl"] button,
    div[data-testid="stSegmentedControl"] [role="group"] button {
        font-size: 18px !important; font-weight: 600 !important;
        padding: 10px 20px !important; min-height: 50px !important;
    }
    div[data-testid="stSegmentedControl"] button p {
        font-size: 18px !important; font-weight: 600 !important;
    }

    /* iPad */
    @media (min-width: 768px) {
        .section-title { font-size: 28px; }
        .now-badge { font-size: 15px; }
        .day-card { width: 110px; min-height: 156px; padding: 14px 10px; }
        .day-num { font-size: 23px; }
        .day-wd { font-size: 13px; }
        .chip { font-size: 13px; padding: 4px 6px; }
        .todo-subj-header { font-size: 18px; }
        [class*="st-key-todo_card_"] input[type="text"] { font-size: 15px; }
        [class*="st-key-todo_card_"] [data-baseweb="select"] { font-size: 15px; }
        .range-item { padding: 16px 20px; }
        .range-item strong { font-size: 18px; }
        .study-time-badge { font-size: 14px; padding: 4px 12px; }
        .point-box, .point-box-blue { padding: 20px 24px; }
        .point-box p, .point-box-blue p,
        .point-box li, .point-box-blue li {
            font-size: 17px !important; line-height: 1.9 !important;
        }
        .point-box h1, .point-box-blue h1,
        .point-box h2, .point-box-blue h2 { font-size: 22px !important; }
        .point-box h3, .point-box-blue h3 { font-size: 19px !important; }
        .toc-sect-title { font-size: 17px; margin: 14px 0 6px; }
        .toc-sub { font-size: 16px; line-height: 1.9; padding: 12px 4px; }
        .st-key-tb_toc div[data-testid="stExpander"] summary,
        .st-key-tb_toc div[data-testid="stExpander"] summary p {
            font-size: 17px !important;
        }
        div.stButton > button { font-size: 16px; min-height: 52px; }
        div[data-testid="stCheckbox"] label p { font-size: 16px; }
        div[data-testid="stSegmentedControl"] button,
        div[data-testid="stSegmentedControl"] [role="group"] button {
            font-size: 22px !important; padding: 14px 28px !important; min-height: 58px !important;
        }
        div[data-testid="stSegmentedControl"] button p { font-size: 22px !important; }
        .tb-cover { width: 240px; }
        .st-key-tb_open_btn_wrap, .st-key-wb_open_btn_wrap { max-width: 260px !important; }

        .wb-detail-title { font-size: 24px; }
        .wb-fc-q { font-size: 42px; }
        .wb-fc-a-shown { font-size: 52px; }
        .wb-fc-a-hidden { font-size: 72px; }
        .wb-fc-meta { font-size: 13px; }
        .wb-fc-lesson { font-size: 17px; }
        .st-key-wb_nav_row button,
        .st-key-tp_nav_row button {
            font-size: 26px !important; min-height: 64px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ===== 教科 × ジャンル =====
SUBJECTS = {
    "social": {"name": "社会", "emoji": "🗺️", "genres": {
        "history": {"name": "歴史", "emoji": "📜"},
        "geography": {"name": "地理", "emoji": "🌏"},
        "civics": {"name": "公民", "emoji": "⚖️"},
    }},
    "japanese": {"name": "国語", "emoji": "📘", "genres": {
        "reading": {"name": "読解", "emoji": "📖"},
        "classic": {"name": "古文・漢文", "emoji": "📜"},
        "kanji": {"name": "漢字・語彙", "emoji": "✍️"},
        "grammar": {"name": "文法", "emoji": "📝"},
    }},
    "math": {"name": "数学", "emoji": "📐", "genres": {
        "general": {"name": "数学", "emoji": "📐"},
    }},
    "science": {"name": "理科", "emoji": "🔬", "genres": {
        "field1": {"name": "第1分野", "emoji": "⚗️"},
        "field2": {"name": "第2分野", "emoji": "🌱"},
    }},
    "english": {"name": "英語", "emoji": "🌐", "genres": {
        "general": {"name": "英語", "emoji": "🌐"},
    }},
}

DATA_DIR = Path(__file__).parent / "data"
JP_WD = ["月", "火", "水", "木", "金", "土", "日"]
DURATION_OPTIONS = ["10分", "15分", "20分", "30分", "45分", "60分", "90分", "120分"]


def _load_excel(subject_key):
    """subject_data.xlsx を GitHub から取得して openpyxl で開く（キャッシュあり）"""
    cache_key = f"_excel_wb_{subject_key}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    import openpyxl, io
    filename = f"{subject_key}_data.xlsx"
    local_path = DATA_DIR / filename
    wb = None
    if local_path.exists():
        wb = openpyxl.load_workbook(local_path, data_only=True)
    else:
        try:
            url = f"https://raw.githubusercontent.com/rebale-minobe/RIA/main/data/{filename}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
        except Exception:
            pass
    st.session_state[cache_key] = wb
    return wb


# ジャンルキー → 日本語シート名マッピング
_GENRE_SHEET_MAP = {
    "history":   "歴史",
    "geography": "地理",
    "civics":    "公民",
    "reading":   "読解",
    "classic":   "古文漢文",
    "kanji":     "漢字語彙",
    "grammar":   "文法",
    "field1":    "第1分野",
    "field2":    "第2分野",
    "general":   "一般",
}


def _genre_jp(genre_key):
    return _GENRE_SHEET_MAP.get(genre_key, genre_key)


def load_textbook(subject_key, genre_key):
    """Excelの「目次_{ジャンル}」シートからJSONと同等の辞書を返す"""
    wb = _load_excel(subject_key)
    if wb is None:
        return None
    sheet_name = f"目次_{_genre_jp(genre_key)}"
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        return None

    # ヘッダー: 編/章番号/章タイトル/節番号/節タイトル/小節番号/小節タイトル/ページ/備考
    chapters_dict = {}
    for row in rows:
        if not any(row):
            continue
        _, ch_num, ch_title, sec_num, sec_title, sub_num, sub_title, page, note = (
            (row + (None,) * 9)[:9]
        )
        if not ch_title:
            continue
        ch_key = ch_num or ch_title
        if ch_key not in chapters_dict:
            chapters_dict[ch_key] = {
                "chapter_number": ch_num or "",
                "title": ch_title,
                "sections": []
            }
        ch = chapters_dict[ch_key]
        # 節を探す or 追加
        sec_key = sec_num or sec_title or "__default__"
        sec = next((s for s in ch["sections"] if s.get("_key") == sec_key), None)
        if sec is None:
            sec = {"_key": sec_key, "title": sec_title or "", "subsections": []}
            ch["sections"].append(sec)
        # 小節を追加
        if sub_title:
            sub_id = f"{subject_key}_{genre_key}_{len(sec['subsections'])}_{''.join(c for c in str(sub_title) if c.isalnum() or c in '_')[:20]}"
            sec["subsections"].append({
                "id": sub_id,
                "number": str(sub_num) if sub_num else "",
                "title": str(sub_title),
                "page": page,
                "note": note or "",
            })

    if not chapters_dict:
        return None

    # JSON互換構造を返す
    genre_jp = _genre_jp(genre_key)
    return {
        "textbook": {
            "subject": subject_key,
            "genre": genre_key,
            "name": f"{genre_jp}教科書",
            "cover_image": f"textbook_covers/{subject_key}_{genre_key}.jpg",
            "chapters": list(chapters_dict.values()),
        }
    }


def load_workbook_answers(subject_key, genre_key):
    """Excelの「ワーク{ジャンル}_解答」シートからJSONと同等の辞書を返す"""
    wb = _load_excel(subject_key)
    if wb is None:
        return None
    genre_jp = _genre_jp(genre_key)
    sheet_name = f"ワーク{genre_jp}_解答"
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        return None

    # ヘッダー: page_number/chapter_number/chapter_title/lesson_title/
    #           section_code/section_name/textbook_ref/workbook_ref/
    #           group_label/q/a/note/context
    pages_dict = {}
    for row in rows:
        if not any(row):
            continue
        r = (row + (None,) * 13)[:13]
        (page_num, ch_num, ch_title, lesson_title,
         sec_code, sec_name, tb_ref, wb_ref,
         group_label, q, a, note, context) = r
        if page_num is None or q is None or a is None:
            continue
        page_num = int(page_num)
        if page_num not in pages_dict:
            pages_dict[page_num] = {
                "page_number": page_num,
                "workbook_ref": wb_ref or "",
                "chapter_number": ch_num or "",
                "chapter_title": ch_title or "",
                "lesson_title": lesson_title or "",
                "sections": []
            }
        pg = pages_dict[page_num]
        # セクション
        sec = next((s for s in pg["sections"]
                    if s["code"] == str(sec_code or "") and s.get("textbook_ref") == (tb_ref or "")), None)
        if sec is None:
            sec = {
                "code": str(sec_code) if sec_code else "",
                "name": str(sec_name) if sec_name else "",
                "textbook_ref": tb_ref or "",
                "groups": []
            }
            pg["sections"].append(sec)
        # グループ
        grp = next((g for g in sec["groups"] if g["label"] == (group_label or "")), None)
        if grp is None:
            grp = {"label": group_label or "", "answers": []}
            sec["groups"].append(grp)
        grp["answers"].append({
            "q": str(q),
            "a": str(a),
            "note": str(note) if note else None,
            "context": str(context) if context else None,
        })

    if not pages_dict:
        return None

    return {
        "subject": subject_key,
        "genre": genre_key,
        "workbook_title": f"{genre_jp}ワーク",
        "cover_image": f"workbook_covers/{subject_key}_{genre_key}.jpg",
        "pages": list(pages_dict.values()),
    }


def flatten_workbook_questions(page):
    """ページ内の全問題を順序保持で1次元リストに展開"""
    flat = []
    for section in page['sections']:
        for group in section['groups']:
            for ans in group['answers']:
                flat.append({
                    'page_number': page['page_number'],
                    'workbook_ref': page.get('workbook_ref', ''),
                    'lesson_title': page.get('lesson_title', ''),
                    'chapter_title': page.get('chapter_title', ''),
                    'section_code': section['code'],
                    'section_name': section['name'],
                    'textbook_ref': section.get('textbook_ref'),
                    'group_label': group.get('label'),
                    'q': ans['q'],
                    'a': ans['a'],
                    'note': ans.get('note'),
                    'context': ans.get('context'),
                })
    return flat


def get_genres_with_toc(subject_key):
    if subject_key not in SUBJECTS:
        return []
    out = []
    for gk, ginfo in SUBJECTS[subject_key]["genres"].items():
        data = load_textbook(subject_key, gk)
        if data and data.get("textbook", {}).get("chapters"):
            out.append((gk, ginfo["name"], data))
    return out


def _get_openai_client():
    """OpenAI クライアントを取得"""
    from openai import OpenAI
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY が Streamlit Secrets に未登録です")
    return OpenAI(api_key=api_key)


def generate_point(title, subject_name, genre_name=""):
    try:
        client = _get_openai_client()
        context = subject_name + (f" / {genre_name}" if genre_name else "")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは中学生に分かりやすく教えるのが得意な先生です。",
                },
                {
                    "role": "user",
                    "content": (
                        f"中学2年生に向けて、{context} の単元「{title}」のポイントを"
                        f"3〜5個まとめて教えてください。\n\n"
                        f"【書式ルール】\n"
                        f"- 冒頭にタイトル行（# や ##）を入れない。いきなり1つ目から始める\n"
                        f"- 各ポイントは「## 絵文字＋短いフレーズ」の見出し、続けて1〜2文の解説\n"
                        f"- 専門用語は分かりやすい言葉に置き換える\n"
                        f"- 親しみやすく、わくわくする口調で"
                    ),
                },
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ エラー: {e}"


def generate_workbook_explanation(question_data, subject_name="社会"):
    """問題に対する解説を生成"""
    try:
        client = _get_openai_client()
        note_line = f"参考: {question_data['note']}\n" if question_data.get('note') else ""
        ctx_line  = f"文脈: {question_data['context']}\n" if question_data.get('context') else ""
        prompt = (
            f"中学2年生の {subject_name} のワーク問題です。\n\n"
            f"単元: {question_data.get('lesson_title','')}\n"
            f"セクション: {question_data['section_name']}\n"
            f"問題番号: {question_data['q']}\n"
            f"正解: {question_data['a']}\n"
            f"{note_line}{ctx_line}\n"
            f"この問題について、中学2年生がよく分かるように2〜4文で解説してください。"
            f"なぜこの答えになるのか、関連する歴史的背景や覚えるポイントを含めてください。\n\n"
            f"【書式】\n"
            f"- 親しみやすい口調で\n"
            f"- マークダウン記号や見出しは使わない、ふつうの文章で\n"
            f"- 前置きは不要、いきなり解説から"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[
                {"role": "system", "content": "あなたは中学生に分かりやすく教えるのが得意な先生です。"},
                {"role": "user",   "content": prompt},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ エラー: {e}"


def render_point_box(text, color="yellow"):
    cls = "point-box" if color == "yellow" else "point-box-blue"
    st.markdown(f"<div class='{cls}'>\n\n{text}\n\n</div>", unsafe_allow_html=True)


# ===== スケジュール =====
STUDY_SCHEDULE = {
    "2026-06-04": [{"subj": "社会"}],
    "2026-06-05": [{"subj": "数学"}],
    "2026-06-06": [{"subj": "国語"}, {"subj": "理科"}],
    "2026-06-07": [{"subj": "社会"}, {"subj": "英語"}],
    "2026-06-08": [{"subj": "数学"}, {"subj": "理科"}],
    "2026-06-09": [{"subj": "国語"}, {"subj": "社会"}],
    "2026-06-10": [{"subj": "英語"}, {"subj": "数学"}],
    "2026-06-11": [{"subj": "保健体育"}, {"subj": "社会"}],
    "2026-06-12": [{"subj": "技術家庭"}, {"subj": "数学"}],
    "2026-06-13": [{"subj": "国語"}, {"subj": "英語"}],
    "2026-06-14": [{"subj": "理科"}, {"subj": "数学"}],
    "2026-06-15": [{"subj": "社会"}, {"subj": "国語"}],
    "2026-06-16": [{"subj": "技術家庭"}, {"subj": "保健体育"}],
    "2026-06-17": [{"subj": "数学"}, {"subj": "英語"}, {"subj": "理科"}],
    "2026-06-18": [
        {"subj": "📝 国語ワーク提出", "type": "submit"},
        {"subj": "TEST", "type": "test"},
    ],
    "2026-06-19": [{"subj": "TEST", "type": "test"}],
}


def render_calendar(schedule, today):
    today_d = today.date()
    days_html = []
    for date_str in sorted(schedule.keys()):
        items = schedule[date_str]
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_today = d == today_d
        is_past = d < today_d
        is_test = any(i.get("type") == "test" for i in items)

        classes = ["day-card"]
        if is_today: classes.append("today")
        if is_test: classes.append("test-day")
        if is_past and not is_today: classes.append("past")

        wd = JP_WD[d.weekday()]
        if d.weekday() == 5: wd_color = "#007AFF"
        elif d.weekday() == 6: wd_color = "#FF3B30"
        else: wd_color = "#8E8E93"

        chips_html = ""
        for it in items:
            subj = it["subj"]
            ctype = it.get("type", "study")
            if ctype == "test":
                chips_html += '<div class="chip chip-test">TEST</div>'
            elif ctype == "submit":
                chips_html += f'<div class="chip chip-submit">{subj.replace("📝 ", "")}</div>'
            else:
                col = subject_color(subj)
                chips_html += (
                    f'<div class="chip" style="'
                    f'background:{col["light"]}; color:{col["primary"]}; '
                    f'border:1px solid {col["primary"]};">{subj}</div>'
                )

        today_marker = '<div class="today-badge">今日</div>' if is_today else ''
        days_html.append(
            f'<div class="{" ".join(classes)}">'
            f'{today_marker}'
            f'<div class="day-num">{d.month}/{d.day}</div>'
            f'<div class="day-wd" style="color:{wd_color};">({wd})</div>'
            f'<div class="chips">{chips_html}</div>'
            f'</div>'
        )

    return f'<div class="calendar-scroll">{"".join(days_html)}</div>'


# ===== データ =====
NEXT_TEST = {
    "name": "1学期 期末テスト", "start_date": "2026-06-18",
    "subjects": [
        {"subject": "技術家庭", "date": "6/18(木)", "time": "9:00", "range": "教科書 P30-55", "study_hours": 2},
        {"subject": "国語", "date": "6/18(木)", "time": "9:45", "range": "漢字 + 文法 + 読解「故郷」 / 📝ワーク提出", "study_hours": 5},
        {"subject": "社会", "date": "6/18(木)", "time": "10:45", "range": "歴史 P105-160", "study_hours": 8},
        {"subject": "保健体育", "date": "6/18(木)", "time": "11:45", "range": "教科書 P20-40", "study_hours": 2},
        {"subject": "数学", "date": "6/19(金)", "time": "9:00", "range": "1年範囲 + 文章題 + 連立方程式", "study_hours": 12},
        {"subject": "英語", "date": "6/19(金)", "time": "10:00", "range": "Unit 1-3 + 英作文", "study_hours": 3},
        {"subject": "理科", "date": "6/19(金)", "time": "10:55", "range": "化学変化 + 生物", "study_hours": 4},
    ]
}

TODO_TODAY = [
    {"subject_name": "社会",  "task": "歴史 P105-130 教科書通読", "duration": "60分", "done": False},
    {"subject_name": "数学",  "task": "1年範囲 P225-248 復習",     "duration": "30分", "done": False},
    {"subject_name": "国語",  "task": "漢字テスト範囲 10個",       "duration": "20分", "done": True},
]

TODAY_TIMETABLE = [
    {"period": 1, "subject": "国語", "subject_key": "japanese"},
    {"period": 2, "subject": "数学", "subject_key": "math"},
    {"period": 3, "subject": "社会", "subject_key": "social"},
    {"period": 4, "subject": "理科", "subject_key": "science"},
    {"period": 5, "subject": "英語", "subject_key": "english"},
    {"period": 6, "subject": "音楽", "subject_key": None},
]

TOMORROW_TIMETABLE = [
    {"period": 1, "subject": "数学", "next_chapter": "連立方程式の応用", "page": "P232"},
    {"period": 2, "subject": "社会", "next_chapter": "江戸幕府の成立", "page": "P124"},
    {"period": 3, "subject": "保健体育", "next_chapter": "運動と健康", "page": "P25"},
    {"period": 4, "subject": "国語", "next_chapter": "古文入門", "page": "P88"},
    {"period": 5, "subject": "技術", "next_chapter": "木材加工", "page": "P40"},
    {"period": 6, "subject": "英語", "next_chapter": "Unit 4 - 未来形", "page": "P45"},
]

today = datetime.now()
test_date = datetime.strptime(NEXT_TEST["start_date"], "%Y-%m-%d")
days_until_test = (test_date - today).days
test_wd = JP_WD[test_date.weekday()]
today_wd = JP_WD[today.weekday()]

# ===== 初回起動時のデフォルト =====
if "selected_study" not in st.session_state:
    st.session_state.selected_study = "social"
    st.session_state.current_study_subject = "social"
    st.session_state["genre_radio_social"] = "歴史"
    st.session_state.detail_subject = "social"
    st.session_state.detail_genre = "history"
    st.session_state.detail_type = "textbook"

if "todo_done" not in st.session_state:
    st.session_state.todo_done = {i: t["done"] for i, t in enumerate(TODO_TODAY)}

for idx, todo in enumerate(TODO_TODAY):
    if f"todo_task_{idx}" not in st.session_state:
        st.session_state[f"todo_task_{idx}"] = todo["task"]
    if f"todo_dur_{idx}" not in st.session_state:
        if todo["duration"] not in DURATION_OPTIONS:
            DURATION_OPTIONS.insert(0, todo["duration"])
        st.session_state[f"todo_dur_{idx}"] = todo["duration"]

# ===== 現在日時 =====
st.markdown(
    f"<div class='now-badge'>🕐 {today.year}年{today.month}月{today.day}日"
    f"（{today_wd}）{today.strftime('%H:%M')}</div>",
    unsafe_allow_html=True
)

# ===== NEXT TEST =====
st.markdown('<div class="section-title">⏳ NEXT TEST</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="test-card">
    <div style="font-size: 17px; opacity: 0.95; font-weight: 600;">{NEXT_TEST['name']} まで</div>
    <div style="display: flex; align-items: baseline; justify-content: center; gap: 10px; margin: 12px 0;">
        <span style="font-size: 68px; font-weight: 800; line-height: 1;">{days_until_test}</span>
        <span style="font-size: 26px; font-weight: 700;">日</span>
    </div>
    <div style="font-size: 13px; opacity: 0.9;">開始: {NEXT_TEST['start_date']}（{test_wd}）</div>
</div>
""", unsafe_allow_html=True)

# ===== Schedule =====
st.markdown('<div class="section-title">📆 Schedule</div>', unsafe_allow_html=True)
st.markdown(render_calendar(STUDY_SCHEDULE, today), unsafe_allow_html=True)

# ===== TEST詳細 =====
btn_label = "📋 TEST詳細を閉じる" if st.session_state.get("show_test_detail") else "📋 TEST詳細を見る"
if st.button(btn_label, key="toggle_test_detail", use_container_width=True):
    st.session_state["show_test_detail"] = not st.session_state.get("show_test_detail", False)

if st.session_state.get("show_test_detail"):
    total_hours = sum(s["study_hours"] for s in NEXT_TEST["subjects"])
    daily = total_hours / max(days_until_test, 1)
    st.markdown(f"**推奨勉強時間 合計: {total_hours} 時間**"
                f"（残り {days_until_test} 日 → 1日 約{daily:.1f}時間）")
    for s in NEXT_TEST["subjects"]:
        col = subject_color(s['subject'])
        st.markdown(f"""
        <div class="range-item" style="border-left-color:{col['primary']};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color:{col['primary']}; font-size: 16px;">{col['emoji']} {s['subject']}</strong>
                <span class="study-time-badge" style="background:{col['primary']};">⏱ {s['study_hours']}h</span>
            </div>
            <div style="font-size: 13px; color: #8E8E93; margin-top: 6px;">
                📅 {s['date']} {s['time']}<br>📖 {s['range']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ===== Today's To Do =====
st.markdown('<div class="section-title">📌 Today\'s To Do</div>', unsafe_allow_html=True)
done_count = sum(1 for v in st.session_state.todo_done.values() if v)
st.markdown(f"今日のタスク: **{done_count}/{len(TODO_TODAY)}** 完了 🎯")

n_per_row = 3
for row_start in range(0, len(TODO_TODAY), n_per_row):
    cols = st.columns(n_per_row)
    for ci in range(n_per_row):
        idx = row_start + ci
        if idx >= len(TODO_TODAY):
            with cols[ci]: st.empty()
            continue
        todo = TODO_TODAY[idx]
        is_done = st.session_state.todo_done.get(idx, todo["done"])
        col = subject_color(todo["subject_name"])

        with cols[ci]:
            container_key = f"todo_card_{idx}"
            opacity = "0.55" if is_done else "1"
            bg = "#F2F2F7" if is_done else "white"
            text_deco = "line-through" if is_done else "none"

            st.markdown(f"""
            <style>
            .st-key-{container_key} {{
                border: 2px solid {col['primary']} !important;
                background: {bg} !important;
                opacity: {opacity};
            }}
            </style>
            """, unsafe_allow_html=True)

            with st.container(key=container_key):
                st.markdown(
                    f"<div class='todo-subj-header' style='color:{col['primary']}; text-decoration:{text_deco};'>"
                    f"{col['emoji']} {todo['subject_name']}</div>",
                    unsafe_allow_html=True
                )
                st.text_input("タスク内容", key=f"todo_task_{idx}",
                              label_visibility="collapsed", placeholder="タスク内容")
                st.selectbox("時間", DURATION_OPTIONS,
                             key=f"todo_dur_{idx}", label_visibility="collapsed")
                btn_label2 = "↩️ 戻す" if is_done else "✅ できた！"
                if st.button(btn_label2, key=f"todo_btn_{idx}", use_container_width=True):
                    st.session_state.todo_done[idx] = not is_done
                    st.rerun()

st.caption("💡 タスクや時間をタップして編集できます")

# ===== 今日の問題（過去に間違えた問題を反復出題） =====
st.markdown('<div class="section-title">📌 今日の問題 <span style="font-size:14px; color:#8E8E93; font-weight:500;">— 反復学習</span></div>', unsafe_allow_html=True)

if not ANSWER_LOG_AVAILABLE:
    st.info("⏳ 解答ログ機能の準備中（modules/answer_log.py を配置してください）")
else:
    # キャッシュキー: 教科横断の未解決問題リスト
    cache_key = "tp_questions_cache"
    if cache_key not in st.session_state:
        with st.spinner("間違えた問題を読み込み中..."):
            try:
                unsolved = answer_log.get_unsolved_questions()
                random.shuffle(unsolved)
                st.session_state[cache_key] = [
                    answer_log.log_to_question(log) for log in unsolved
                ]
            except Exception as e:
                st.error(f"ログ読み込みエラー: {e}")
                st.session_state[cache_key] = []

    tp_questions = st.session_state.get(cache_key, [])
    tp_total = len(tp_questions)

    if tp_total == 0:
        st.success("🎉 反復学習する問題がありません！全問正解おめでとう！")
        st.caption("ワークで×を付けた問題が、次の日からここに自動で出題されます。")
    else:
        st.markdown(
            f"📚 復習する問題: **{tp_total} 問**  "
            f"<span style='color:#8E8E93;'>（過去に間違えた問題を教科横断でシャッフル出題）</span>",
            unsafe_allow_html=True
        )

        # 現在位置
        tp_idx_key = "tp_idx"
        if tp_idx_key not in st.session_state:
            st.session_state[tp_idx_key] = 0
        tp_pos = max(0, min(st.session_state[tp_idx_key], tp_total - 1))
        st.session_state[tp_idx_key] = tp_pos
        tp_current = tp_questions[tp_pos]

        # 進捗
        tp_correct = sum(1 for i in range(tp_total)
                        if st.session_state.get(f"tp_result_{i}") == "maru")
        tp_wrong = sum(1 for i in range(tp_total)
                      if st.session_state.get(f"tp_result_{i}") == "batsu")
        st.markdown(f"""
        <div class='wb-progress-row'>
            <span>問題 <b>{tp_pos + 1}</b> / {tp_total}</span>
            <span>
                <span style='color:#007AFF;'>⭕ {tp_correct}</span>　
                <span style='color:#FF3B30;'>❌ {tp_wrong}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.progress((tp_pos + 1) / tp_total)

        # フラッシュカード（答え常時表示）
        tp_result = st.session_state.get(f"tp_result_{tp_pos}")

        # 教科バッジ + メタ
        subj_name = tp_current.get('subject_name', '')
        genre_name = tp_current.get('genre_name', '')
        subj_col = subject_color(subj_name)
        tp_meta_parts = []
        if tp_current.get('section_code'):
            tp_meta_parts.append(f"{tp_current['section_code']} {tp_current.get('section_name','')}")
        if tp_current.get('group_label'):
            tp_meta_parts.append(tp_current['group_label'])
        if tp_current.get('workbook_ref'):
            tp_meta_parts.append(tp_current['workbook_ref'])
        if tp_current.get('textbook_ref'):
            tp_meta_parts.append(tp_current['textbook_ref'])

        subject_badge_html = (
            f'<div style="display:inline-block; background:{subj_col["light"]}; '
            f'color:{subj_col["primary"]}; padding:4px 14px; border-radius:14px; '
            f'font-size:13px; font-weight:700; margin-bottom:6px;">'
            f'{subj_col["emoji"]} {subj_name}'
            + (f' / {genre_name}' if genre_name else '')
            + '</div>'
        )

        tp_card_html = f"""
        <div class='wb-flashcard' style='border-color:{subj_col["primary"]};'>
            <div class='wb-fc-header'>
                {subject_badge_html}
                <div class='wb-fc-meta'>{' ／ '.join(tp_meta_parts)}</div>
                <div class='wb-fc-lesson'>{tp_current.get('lesson_title','')}</div>
            </div>
            <div class='wb-fc-q' style='color:{subj_col["primary"]};'>{tp_current['q']}</div>
            <div class='wb-fc-divider'></div>
            <div class='wb-fc-a-area'>
                <div class='wb-fc-a-shown'>{tp_current['a']}</div>
            </div>
        </div>
        """
        st.markdown(tp_card_html, unsafe_allow_html=True)

        # 注記と結果バッジ
        tp_info_lines = []
        if tp_current.get('note'):
            tp_info_lines.append(f"※ {tp_current['note']}")
        if tp_current.get('context'):
            tp_info_lines.append(f"💭 {tp_current['context']}")
        if tp_info_lines:
            st.caption(" ／ ".join(tp_info_lines))
        if tp_result == "maru":
            st.markdown("<div class='wb-result-badge maru'>⭕ 覚えた！</div>", unsafe_allow_html=True)
        elif tp_result == "batsu":
            st.markdown("<div class='wb-result-badge batsu'>❌ もう一度</div>", unsafe_allow_html=True)

        # ナビゲーション (◀ ⭕ ❌ 💡 ▶)
        with st.container(key="tp_nav_row"):
            tp_nav_cols = st.columns(5)
            with tp_nav_cols[0]:
                if st.button("◀", key=f"tp_prev_{tp_pos}",
                            disabled=(tp_pos == 0), use_container_width=True):
                    st.session_state[tp_idx_key] = tp_pos - 1
                    st.rerun()
            with tp_nav_cols[1]:
                if st.button("⭕", key=f"tp_maru_{tp_pos}",
                            use_container_width=True, help="覚えた！"):
                    st.session_state[f"tp_result_{tp_pos}"] = "maru"
                    # バッファに追加（5件溜まったら一括 push）
                    if "tp_pending_logs" not in st.session_state:
                        st.session_state["tp_pending_logs"] = []
                    try:
                        entry = answer_log.question_to_log_entry(
                            tp_current,
                            tp_current.get('subject_key', ''),
                            tp_current.get('subject_name', ''),
                            tp_current.get('genre_key', ''),
                            tp_current.get('genre_name', ''),
                            "maru"
                        )
                        st.session_state["tp_pending_logs"].append(entry)
                        if len(st.session_state["tp_pending_logs"]) >= 5:
                            answer_log.append_logs_batch(st.session_state["tp_pending_logs"])
                            st.session_state["tp_pending_logs"] = []
                    except Exception:
                        pass
                    if tp_pos < tp_total - 1:
                        st.session_state[tp_idx_key] = tp_pos + 1
                    st.rerun()
            with tp_nav_cols[2]:
                if st.button("❌", key=f"tp_batsu_{tp_pos}",
                            use_container_width=True, help="まだ覚えてない"):
                    st.session_state[f"tp_result_{tp_pos}"] = "batsu"
                    if "tp_pending_logs" not in st.session_state:
                        st.session_state["tp_pending_logs"] = []
                    try:
                        entry = answer_log.question_to_log_entry(
                            tp_current,
                            tp_current.get('subject_key', ''),
                            tp_current.get('subject_name', ''),
                            tp_current.get('genre_key', ''),
                            tp_current.get('genre_name', ''),
                            "batsu"
                        )
                        st.session_state["tp_pending_logs"].append(entry)
                        if len(st.session_state["tp_pending_logs"]) >= 5:
                            answer_log.append_logs_batch(st.session_state["tp_pending_logs"])
                            st.session_state["tp_pending_logs"] = []
                    except Exception:
                        pass
                    if tp_pos < tp_total - 1:
                        st.session_state[tp_idx_key] = tp_pos + 1
                    st.rerun()
            with tp_nav_cols[3]:
                if st.button("💡", key=f"tp_explain_{tp_pos}",
                            use_container_width=True, help="解説を見る"):
                    with st.spinner("解説生成中..."):
                        st.session_state[f"tp_explain_{tp_pos}"] = (
                            generate_workbook_explanation(
                                tp_current,
                                tp_current.get('subject_name', '社会')
                            )
                        )
                    st.rerun()
            with tp_nav_cols[4]:
                if st.button("▶", key=f"tp_next_{tp_pos}",
                            disabled=(tp_pos >= tp_total - 1), use_container_width=True):
                    st.session_state[tp_idx_key] = tp_pos + 1
                    st.rerun()

        # 解説表示
        tp_explain_key = f"tp_explain_{tp_pos}"
        if st.session_state.get(tp_explain_key):
            st.markdown("")
            render_point_box(st.session_state[tp_explain_key], color="yellow")

        # 完了時のリロード（最後の問題に答えたタイミング）
        if tp_pos == tp_total - 1 and tp_result is not None:
            # pending logs を flush
            if st.session_state.get("tp_pending_logs"):
                try:
                    answer_log.append_logs_batch(st.session_state["tp_pending_logs"])
                    st.session_state["tp_pending_logs"] = []
                except Exception:
                    pass

            st.markdown("---")
            tp_still_wrong = sum(1 for i in range(tp_total)
                                if st.session_state.get(f"tp_result_{i}") == "batsu")
            if tp_still_wrong > 0:
                st.warning(f"❌ まだ {tp_still_wrong} 問 覚えきれてません")
            else:
                st.success("🎉 全問正解！")
            if st.button("🔄 「今日の問題」を再読み込み", key="tp_reload",
                         use_container_width=True, type="primary"):
                keys_to_clear = [k for k in list(st.session_state.keys())
                                if k.startswith("tp_")]
                for k in keys_to_clear:
                    del st.session_state[k]
                st.rerun()

# ===== 今日の時間割 =====
st.markdown('<div class="section-title">📅 今日の時間割</div>', unsafe_allow_html=True)

for p in TODAY_TIMETABLE:
    pn = p['period']
    col = subject_color(p['subject'])
    with st.expander(f"**{pn}**　{col['emoji']} {p['subject']}", expanded=False):
        skey = p.get("subject_key")
        gtocs = get_genres_with_toc(skey) if skey else []

        if gtocs:
            if len(gtocs) > 1:
                gnames = [g[1] for g in gtocs]
                sel_gname = st.radio("ジャンル", gnames, horizontal=True,
                                     key=f"today_grad_{pn}", label_visibility="collapsed")
                _, _, tdata = next(g for g in gtocs if g[1] == sel_gname)
            else:
                _, _, tdata = gtocs[0]

            chapters = tdata["textbook"]["chapters"]
            chapter_labels = [
                f"{c.get('chapter_number','').strip()} {c.get('title','').strip()}".strip()
                for c in chapters
            ]
            sel_ch = st.selectbox("章", chapter_labels, index=None,
                                  placeholder="章を選択...",
                                  key=f"today_ch_{pn}", label_visibility="collapsed")
            if sel_ch:
                ch_idx = chapter_labels.index(sel_ch)
                chap = chapters[ch_idx]
                sub_opts = []
                for sec in chap.get("sections", []):
                    for sub in sec.get("subsections", []):
                        sub_opts.append(f"{sub['title']} (p.{sub['page']})")
                if sub_opts:
                    st.multiselect("項目", sub_opts,
                                   placeholder="やった項目を選択（複数可）",
                                   key=f"today_subs_{pn}", label_visibility="collapsed")
        else:
            st.text_input("範囲", placeholder="今日やった範囲（例: P30-45）",
                          key=f"today_range_{pn}", label_visibility="collapsed")

if st.button("✅ 全部記録する", use_container_width=True, type="primary", key="record_today_all"):
    records = []
    for p in TODAY_TIMETABLE:
        pn = p['period']
        skey = p.get("subject_key")
        gtocs = get_genres_with_toc(skey) if skey else []
        if gtocs:
            ch_val = st.session_state.get(f"today_ch_{pn}")
            subs_val = st.session_state.get(f"today_subs_{pn}", [])
            if ch_val and subs_val:
                records.append(f"**{p['subject']}**: {ch_val}（{len(subs_val)}項目）")
        else:
            range_val = st.session_state.get(f"today_range_{pn}", "")
            if range_val:
                records.append(f"**{p['subject']}**: {range_val}")
    if records:
        st.success("📝 " + str(len(records)) + " 件記録しました！\n\n" + "\n\n".join(f"・ {r}" for r in records))
    else:
        st.warning("記録する内容がありません。各教科を開いて範囲を入力してください。")

# ===== 明日の予習 =====
st.markdown('<div class="section-title">🔮 明日の予習</div>', unsafe_allow_html=True)
for p in TOMORROW_TIMETABLE:
    pn = p['period']
    col = subject_color(p['subject'])
    with st.expander(f"**{pn}**　{col['emoji']} {p['subject']}", expanded=False):
        st.markdown(f"📖 次回学習：**{p['next_chapter']}**（{p['page']}）")
        point_key = f"tm_point_text_{pn}"
        if st.button("💡 ポイントを見る", key=f"tm_point_{pn}", use_container_width=True):
            with st.spinner("ポイント生成中..."):
                st.session_state[point_key] = generate_point(p['next_chapter'], p['subject'])
        if st.session_state.get(point_key):
            render_point_box(st.session_state[point_key], color="blue")

# ===== Study (教科書/ワーク) =====
st.markdown('<div class="section-title">📚 教科書/ワーク</div>', unsafe_allow_html=True)

subject_keys = list(SUBJECTS.keys())
subject_labels = [SUBJECTS[k]['name'] for k in subject_keys]

current_label = None
if st.session_state.get("selected_study") in SUBJECTS:
    cs = st.session_state.selected_study
    current_label = SUBJECTS[cs]['name']

selected_label = st.segmented_control(
    "教科", subject_labels, default=current_label,
    label_visibility="collapsed", key="subject_seg"
)
if selected_label:
    idx = subject_labels.index(selected_label)
    new_skey = subject_keys[idx]
    if st.session_state.get("selected_study") != new_skey:
        st.session_state.selected_study = new_skey
        st.session_state.pop("detail_type", None)
        st.rerun()

if "selected_study" in st.session_state and st.session_state.selected_study in SUBJECTS:
    skey = st.session_state.selected_study
    sinfo = SUBJECTS[skey]
    genre_keys = list(sinfo["genres"].keys())

    if st.session_state.get("current_study_subject") != skey:
        st.session_state.current_study_subject = skey
        st.session_state.pop("detail_type", None)

    st.markdown("---")

    if len(genre_keys) > 1:
        genre_display = {}
        for gk in genre_keys:
            gi = sinfo["genres"][gk]
            genre_display[gi['name']] = gk
        sel_label = st.radio("ジャンル", list(genre_display.keys()),
                             horizontal=True, label_visibility="collapsed",
                             key=f"genre_radio_{skey}")
        gkey = genre_display[sel_label]
    else:
        gkey = genre_keys[0]
    ginfo = sinfo["genres"][gkey]

    tb_data = load_textbook(skey, gkey)
    wb_data = load_workbook_answers(skey, gkey)

    # 教科書/ワーク 切替
    material_options = []
    if tb_data: material_options.append("📖 教科書")
    if wb_data: material_options.append("📝 ワーク")

    sel_material = None
    if not material_options:
        st.markdown('<div class="cover-ph">📖 教科書・ワーク 未登録</div>', unsafe_allow_html=True)
        st.caption("「教科書登録」「ワーク解答登録」ページから登録できます")
    elif len(material_options) > 1:
        sel_material = st.radio(
            "教材", material_options,
            horizontal=True, label_visibility="collapsed",
            key=f"material_type_{skey}_{gkey}"
        )
    else:
        sel_material = material_options[0]

    # === 教科書モード ===
    if sel_material == "📖 教科書" and tb_data:
        tb = tb_data["textbook"]
        if tb.get("cover_image"):
            cover_path = DATA_DIR / tb["cover_image"]
            if cover_path.exists():
                with open(cover_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(f"""
                <div class="tb-cover-wrap">
                    <img src="data:image/jpeg;base64,{b64}" class="tb-cover" alt="教科書">
                </div>
                """, unsafe_allow_html=True)
        with st.container(key="tb_open_btn_wrap"):
            if st.button("📖 目次を見る", key=f"open_tb_{skey}_{gkey}",
                         use_container_width=True, type="primary"):
                st.session_state.detail_subject = skey
                st.session_state.detail_genre = gkey
                st.session_state.detail_type = "textbook"
                st.rerun()

    # === ワークモード ===
    if sel_material == "📝 ワーク" and wb_data:
        if wb_data.get("cover_image"):
            cover_path = DATA_DIR / wb_data["cover_image"]
            if cover_path.exists():
                with open(cover_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(f"""
                <div class="tb-cover-wrap">
                    <img src="data:image/jpeg;base64,{b64}" class="tb-cover" alt="ワーク">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="cover-ph">📝 {wb_data.get("workbook_title", "ワーク")}</div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="cover-ph">📝 {wb_data.get("workbook_title", "ワーク")}<br>'
                f'<small style="opacity:0.7;">表紙未登録</small></div>',
                unsafe_allow_html=True
            )

        with st.container(key="wb_open_btn_wrap"):
            if st.button("📋 解答を見る", key=f"open_wb_{skey}_{gkey}",
                         use_container_width=True, type="primary"):
                st.session_state.detail_subject = skey
                st.session_state.detail_genre = gkey
                st.session_state.detail_type = "workbook"
                st.rerun()

    # === 教科書詳細 (目次) ===
    if (st.session_state.get("detail_type") == "textbook"
        and st.session_state.get("detail_genre") == gkey
        and st.session_state.get("detail_subject") == skey):
        ddata = load_textbook(st.session_state.detail_subject, st.session_state.detail_genre)
        if ddata:
            st.markdown("---")
            st.markdown(
                f"<div class='wb-detail-title'>📄 目次 — {ddata['textbook'].get('name', '')}</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='font-size:13px; color:#8E8E93; margin-bottom:10px;'>"
                "章を開いて、各項目の「💡」でポイントを見られます ✨</div>",
                unsafe_allow_html=True
            )

            with st.container(key="tb_toc"):
                for chapter in ddata["textbook"]["chapters"]:
                    ch_title = f"{chapter.get('chapter_number', '')} {chapter['title']}"
                    with st.expander(f"📖 {ch_title}"):
                        for section in chapter.get("sections", []):
                            if section.get("title"):
                                st.markdown(
                                    f"<div class='toc-sect-title'>{section['title']}</div>",
                                    unsafe_allow_html=True
                                )
                            for sub in section.get("subsections", []):
                                c1, c2 = st.columns([1, 6])
                                with c1:
                                    if st.button("💡", key=f"pt_{sub['id']}", help="ポイントを見る"):
                                        with st.spinner("生成中..."):
                                            st.session_state[f"pt_text_{sub['id']}"] = generate_point(
                                                sub["title"], subject_name=sinfo['name'],
                                                genre_name=ginfo['name']
                                            )
                                with c2:
                                    st.markdown(
                                        f"<div class='toc-sub'>{sub['title']} "
                                        f"<span class='toc-page'>(p.{sub['page']})</span></div>",
                                        unsafe_allow_html=True
                                    )
                                pt_key = f"pt_text_{sub['id']}"
                                if st.session_state.get(pt_key):
                                    render_point_box(st.session_state[pt_key], color="yellow")

    # === ワーク詳細 (フラッシュカード) ===
    if (st.session_state.get("detail_type") == "workbook"
        and st.session_state.get("detail_genre") == gkey
        and st.session_state.get("detail_subject") == skey):
        wbd = load_workbook_answers(st.session_state.detail_subject, st.session_state.detail_genre)
        if wbd and wbd.get("pages"):
            st.markdown("---")
            st.markdown(
                f"<div class='wb-detail-title'>📋 {wbd.get('workbook_title', '')}</div>",
                unsafe_allow_html=True
            )

            # ページ選択
            page_options = [
                f"P.{p['page_number']}　{p.get('lesson_title','')}"
                for p in wbd["pages"]
            ]
            sel_page_label = st.selectbox(
                "📄 ページを選択", page_options,
                key=f"wb_page_sel_{skey}_{gkey}",
            )
            page_idx = page_options.index(sel_page_label)
            page = wbd["pages"][page_idx]
            page_num = page['page_number']

            # 問題フラット化
            questions = flatten_workbook_questions(page)
            total = len(questions)

            if total == 0:
                st.warning("このページに登録された問題がありません")
            else:
                # モード判定
                mode_key = f"wb_mode_{page_num}"
                mode = st.session_state.get(mode_key, "normal")

                # アクティブインデックスリスト
                if mode == "normal":
                    active = list(range(total))
                else:
                    active = [i for i in range(total)
                             if st.session_state.get(f"wb_result_{page_num}_{i}") == "batsu"]
                    if not active:
                        st.session_state[mode_key] = "normal"
                        active = list(range(total))
                        mode = "normal"

                n_active = len(active)

                # 現在位置
                idx_key = f"wb_idx_{page_num}_{mode}"
                if idx_key not in st.session_state:
                    st.session_state[idx_key] = 0
                cur_pos = max(0, min(st.session_state[idx_key], n_active - 1))
                st.session_state[idx_key] = cur_pos
                original_idx = active[cur_pos]
                current = questions[original_idx]

                # モードバッジ
                if mode == "retest":
                    st.markdown(
                        f"<div class='wb-mode-badge wb-mode-retest'>🔄 再テストモード（×問題のみ）</div>",
                        unsafe_allow_html=True
                    )

                # 進捗
                correct = sum(1 for i in range(total)
                             if st.session_state.get(f"wb_result_{page_num}_{i}") == "maru")
                wrong = sum(1 for i in range(total)
                           if st.session_state.get(f"wb_result_{page_num}_{i}") == "batsu")

                # ×カウント（batsuのみ）
                wrong = sum(1 for i in range(total)
                            if st.session_state.get(f"wb_result_{page_num}_{i}") == "batsu")
                st.markdown(f"""
                <div class='wb-progress-row'>
                    <span>問題 <b>{cur_pos + 1}</b> / {n_active}</span>
                    <span style='color:#FF3B30; font-weight:700;'>
                        {"❌ " + str(wrong) + " 問" if wrong else ""}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                st.progress((cur_pos + 1) / n_active)

                # 現在の×状態
                result = st.session_state.get(f"wb_result_{page_num}_{original_idx}")

                # ヘッダー情報
                meta_parts = []
                meta_parts.append(f"{current.get('section_code','')} {current.get('section_name','')}")
                if current.get('group_label'):
                    meta_parts.append(current['group_label'])
                if current.get('workbook_ref'):
                    meta_parts.append(current['workbook_ref'])
                if current.get('textbook_ref'):
                    meta_parts.append(current['textbook_ref'])

                # ×バッジをカードボーダーに反映
                border_color = "#FF3B30" if result == "batsu" else "#FF9500"
                card_html = f"""
                <div class='wb-flashcard' style='border-color:{border_color};'>
                    <div class='wb-fc-header'>
                        <div class='wb-fc-meta'>{' ／ '.join(meta_parts)}</div>
                        <div class='wb-fc-lesson'>{current.get('lesson_title','')}</div>
                    </div>
                    <div class='wb-fc-q'>{current['q']}</div>
                    <div class='wb-fc-divider'></div>
                    <div class='wb-fc-a-area'>
                        <div class='wb-fc-a-shown'>{current['a']}</div>
                    </div>
                    {('<div style="text-align:center;margin-top:8px;font-size:13px;'
                      'color:#FF3B30;font-weight:700;letter-spacing:0.03em;">❌ もう一度</div>')
                     if result == "batsu" else ''}
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

                # 注記
                info_lines = []
                if current.get('note'):    info_lines.append(f"※ {current['note']}")
                if current.get('context'): info_lines.append(f"💭 {current['context']}")
                if info_lines:
                    st.caption(" ／ ".join(info_lines))

                # ナビゲーション (◀  ❌toggle  💡  ▶) — 4ボタン
                with st.container(key="wb_nav_row"):
                    nav_cols = st.columns([1, 1.2, 1.2, 1.6])

                    # ◀ 前へ
                    with nav_cols[0]:
                        if st.button("◀", key=f"prev_{page_num}_{original_idx}",
                                     disabled=(cur_pos == 0), use_container_width=True,
                                     help="前の問題"):
                            st.session_state[idx_key] = cur_pos - 1
                            st.rerun()

                    # ❌ トグル（押すと×、もう一度押すと解除）
                    with nav_cols[1]:
                        batsu_label = "❌ 消す" if result == "batsu" else "❌"
                        if st.button(batsu_label, key=f"batsu_{page_num}_{original_idx}",
                                     use_container_width=True, help="わからなかった問題にマーク"):
                            if result == "batsu":
                                # トグルOFF → 削除
                                st.session_state.pop(f"wb_result_{page_num}_{original_idx}", None)
                            else:
                                # トグルON → batsu記録
                                st.session_state[f"wb_result_{page_num}_{original_idx}"] = "batsu"
                                if ANSWER_LOG_AVAILABLE:
                                    if "wb_pending_logs" not in st.session_state:
                                        st.session_state["wb_pending_logs"] = []
                                    try:
                                        entry = answer_log.question_to_log_entry(
                                            current, skey, sinfo['name'],
                                            gkey, ginfo['name'], "batsu"
                                        )
                                        st.session_state["wb_pending_logs"].append(entry)
                                        if len(st.session_state["wb_pending_logs"]) >= 5:
                                            answer_log.append_logs_batch(st.session_state["wb_pending_logs"])
                                            st.session_state["wb_pending_logs"] = []
                                    except Exception:
                                        pass
                            st.rerun()

                    # 💡 解説
                    with nav_cols[2]:
                        if st.button("💡", key=f"explain_{page_num}_{original_idx}",
                                     use_container_width=True, help="解説を見る"):
                            with st.spinner("解説生成中..."):
                                st.session_state[f"wb_explain_{page_num}_{original_idx}"] = (
                                    generate_workbook_explanation(current, sinfo['name'])
                                )
                            st.rerun()

                    # ▶ 次へ（主アクション）
                    with nav_cols[3]:
                        if cur_pos < n_active - 1:
                            if st.button("次へ ▶", key=f"next_{page_num}_{original_idx}",
                                         use_container_width=True, help="次の問題"):
                                st.session_state[idx_key] = cur_pos + 1
                                st.rerun()
                        else:
                            st.button("最後", key=f"next_{page_num}_{original_idx}",
                                      use_container_width=True, disabled=True)

                # 解説表示
                explain_key = f"wb_explain_{page_num}_{original_idx}"
                if st.session_state.get(explain_key):
                    st.markdown("")
                    render_point_box(st.session_state[explain_key], color="yellow")

                # ページ完了時（最後の問題に到達）
                if cur_pos == n_active - 1:
                    # pending logs flush
                    if ANSWER_LOG_AVAILABLE and st.session_state.get("wb_pending_logs"):
                        try:
                            answer_log.append_logs_batch(st.session_state["wb_pending_logs"])
                            st.session_state["wb_pending_logs"] = []
                        except Exception:
                            pass

                    wrong_indices = [i for i in range(total)
                                     if st.session_state.get(f"wb_result_{page_num}_{i}") == "batsu"]
                    st.markdown("---")
                    if wrong_indices:
                        st.warning(f"❌ {len(wrong_indices)} 問にマークあり")
                        if mode == "normal":
                            if st.button(f"🔄 ×の {len(wrong_indices)} 問で再テスト",
                                         use_container_width=True, type="primary",
                                         key=f"start_retest_{page_num}"):
                                st.session_state[mode_key] = "retest"
                                st.session_state[f"wb_idx_{page_num}_retest"] = 0
                                st.rerun()
                        else:
                            if st.button("↩️ 通常モードに戻る",
                                         use_container_width=True,
                                         key=f"back_normal_{page_num}"):
                                st.session_state[mode_key] = "normal"
                                st.rerun()
                    else:
                        st.success("🎉 全問チェック完了！")

                    if st.button("🗑️ このページの×をリセット",
                                 key=f"reset_{page_num}",
                                 use_container_width=True):
                        for i in range(total):
                            st.session_state.pop(f"wb_result_{page_num}_{i}", None)
                            st.session_state.pop(f"wb_explain_{page_num}_{i}", None)
                        st.session_state[mode_key] = "normal"
                        st.session_state[f"wb_idx_{page_num}_normal"] = 0
                        st.rerun()

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | TOP ページ v1.3")
