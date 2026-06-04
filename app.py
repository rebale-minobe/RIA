"""
RIA TOP ページ v1.2
v1.2 追加:
- 教科書 / ワーク 切り替え (radio)
- ワーク表紙表示 + 「📋 解答を見る」ボタン
- ワーク詳細: ページ選択 → セクション → 問題ごとに「タップで答え」表示
- 全部表示/全部隠す ボタン
"""

import streamlit as st
import json
import requests
import base64
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="RIA", page_icon="🌟", layout="wide", initial_sidebar_state="collapsed")

# ===== カラーパレット =====
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

    /* ワーク解答 */
    .wb-detail-title {
        font-size: 20px; font-weight: 700; color: #1c1c1e;
        margin: 8px 0 4px 0;
    }
    .wb-section-head {
        font-size: 15px; font-weight: 700;
        background: #FFF4E5; color: #b8331f;
        padding: 8px 12px; border-radius: 8px;
        margin: 14px 0 6px 0;
    }
    .wb-group-label {
        font-weight: 700; font-size: 14px;
        color: #FF6B00; margin: 8px 0 4px 0;
    }
    .wb-ans-q {
        font-weight: 700; font-size: 16px;
        color: #FF9500; padding-top: 6px; text-align: center;
    }
    .wb-ans-revealed {
        background: linear-gradient(135deg, #E8F8EE, #C8F0D8);
        color: #1c1c1e; font-weight: 600;
        padding: 10px 14px; border-radius: 10px;
        border-left: 4px solid #34C759;
        font-size: 15px; line-height: 1.55;
        animation: ansReveal 0.3s ease-out;
    }
    @keyframes ansReveal {
        from { opacity: 0; transform: translateY(-4px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .wb-ans-note { color: #AF52DE; font-size: 12px; margin-left: 6px; }
    .st-key-wb_ans_row div[data-testid="stButton"] button {
        background: #FFF8E1 !important;
        color: #8E6800 !important;
        font-size: 13px !important;
        border: 1px dashed #FFCC00 !important;
        min-height: 38px !important;
        font-weight: 500 !important;
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

    /* ボタン */
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

    /* segmented_control */
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
        .wb-section-head { font-size: 17px; padding: 10px 14px; }
        .wb-ans-q { font-size: 18px; }
        .wb-ans-revealed { font-size: 17px; padding: 12px 16px; }
        .st-key-wb_ans_row div[data-testid="stButton"] button {
            font-size: 14px !important; min-height: 44px !important;
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


def load_textbook(subject_key, genre_key):
    filename = f"{subject_key}_{genre_key}_textbook.json"
    local_path = DATA_DIR / filename
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    try:
        url = f"https://raw.githubusercontent.com/MinobeHiroshi/RIA/main/data/{filename}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def load_workbook_answers(subject_key, genre_key):
    filename = f"{subject_key}_{genre_key}_workbook_answers.json"
    local_path = DATA_DIR / filename
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    try:
        url = f"https://raw.githubusercontent.com/MinobeHiroshi/RIA/main/data/{filename}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def get_genres_with_toc(subject_key):
    if subject_key not in SUBJECTS:
        return []
    out = []
    for gk, ginfo in SUBJECTS[subject_key]["genres"].items():
        data = load_textbook(subject_key, gk)
        if data and data.get("textbook", {}).get("chapters"):
            out.append((gk, ginfo["name"], data))
    return out


def generate_point(title, subject_name, genre_name=""):
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ("⚠️ `ANTHROPIC_API_KEY` を Streamlit Secrets に登録すると、"
                    "ここに先生からのポイントが表示されます。")
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        context = subject_name + (f" / {genre_name}" if genre_name else "")
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": (
                    f"中学2年生に向けて、{context} の単元「{title}」のポイントを"
                    f"3〜5個まとめて教えてください。\n\n"
                    f"【書式ルール】\n"
                    f"- 冒頭にタイトル行（# や ##）を入れない。いきなり1つ目から始める\n"
                    f"- 各ポイントは「## 絵文字＋短いフレーズ」の見出し、続けて1〜2文の解説\n"
                    f"- 専門用語は分かりやすい言葉に置き換える\n"
                    f"- 親しみやすく、わくわくする口調で"
                )
            }]
        )
        return msg.content[0].text
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
                btn_label = "↩️ 戻す" if is_done else "✅ できた！"
                if st.button(btn_label, key=f"todo_btn_{idx}", use_container_width=True):
                    st.session_state.todo_done[idx] = not is_done
                    st.rerun()

st.caption("💡 タスクや時間をタップして編集できます")

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
    
    # データロード
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

    # === ワーク詳細 (解答ページ) ===
    if (st.session_state.get("detail_type") == "workbook"
        and st.session_state.get("detail_genre") == gkey
        and st.session_state.get("detail_subject") == skey):
        wbd = load_workbook_answers(st.session_state.detail_subject, st.session_state.detail_genre)
        if wbd and wbd.get("pages"):
            st.markdown("---")
            st.markdown(
                f"<div class='wb-detail-title'>📋 解答 — {wbd.get('workbook_title', '')}</div>",
                unsafe_allow_html=True
            )
            st.caption("各問題のボタンをタップすると答えが表示されます")
            
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
            
            # 章・参照
            chap = f"{page.get('chapter_number','') or ''} {page.get('chapter_title','') or ''}".strip()
            if chap:
                st.markdown(f"📖 **{chap}**")
            if page.get('question_pages_ref'):
                st.caption(f"参照: {page['question_pages_ref']}")
            
            # 全部表示/隠す
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("👁️ 全部表示", key=f"show_all_{page_num}",
                            use_container_width=True):
                    for si, sec in enumerate(page['sections']):
                        for gi, grp in enumerate(sec['groups']):
                            for ai in range(len(grp['answers'])):
                                st.session_state[f"wb_shown_{page_num}_{si}_{gi}_{ai}"] = True
                    st.rerun()
            with col_b:
                if st.button("🔒 全部隠す", key=f"hide_all_{page_num}",
                            use_container_width=True):
                    for si, sec in enumerate(page['sections']):
                        for gi, grp in enumerate(sec['groups']):
                            for ai in range(len(grp['answers'])):
                                st.session_state[f"wb_shown_{page_num}_{si}_{gi}_{ai}"] = False
                    st.rerun()
            
            # セクション
            for si, section in enumerate(page['sections']):
                sec_head_text = f"{section['code']} {section['name']}"
                if section.get('textbook_ref'):
                    sec_head_text += f"　— {section['textbook_ref']}"
                st.markdown(f"<div class='wb-section-head'>{sec_head_text}</div>",
                            unsafe_allow_html=True)
                if section.get('subtitle'):
                    st.caption(section['subtitle'])
                
                for gi, group in enumerate(section['groups']):
                    if group.get('label'):
                        st.markdown(f"<div class='wb-group-label'>{group['label']}</div>",
                                    unsafe_allow_html=True)
                    
                    for ai, ans in enumerate(group['answers']):
                        shown_key = f"wb_shown_{page_num}_{si}_{gi}_{ai}"
                        is_shown = st.session_state.get(shown_key, False)
                        
                        with st.container(key=f"wb_ans_row_{page_num}_{si}_{gi}_{ai}"):
                            cols = st.columns([1, 5])
                            with cols[0]:
                                st.markdown(f"<div class='wb-ans-q'>{ans['q']}</div>",
                                            unsafe_allow_html=True)
                            with cols[1]:
                                if is_shown:
                                    note_html = (
                                        f"<span class='wb-ans-note'>※ {ans['note']}</span>"
                                        if ans.get('note') else ""
                                    )
                                    st.markdown(
                                        f"<div class='wb-ans-revealed'>{ans['a']}{note_html}</div>",
                                        unsafe_allow_html=True
                                    )
                                    if ans.get('context'):
                                        st.caption(f"💭 {ans['context']}")
                                else:
                                    if st.button("👆 タップで答えを見る",
                                                key=f"reveal_{shown_key}",
                                                use_container_width=True):
                                        st.session_state[shown_key] = True
                                        st.rerun()
                st.markdown("")

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | TOP ページ v1.2")
