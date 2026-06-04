"""
RIA TOP ページ v0.8
更新点 (v0.8):
- NEXT TEST 上に「期末テストまでのスケジュールカレンダー」追加
- To Do TODAY をカード化（教科色の左ストライプ＋完了トグル）
- 5教科＋実技4教科を色分け、カレンダー/ToDo/タイムテーブルで統一使用
- 教科書を「タップで開く」（クリック可能なカバー、開くボタン削除）
- 章を開いた中の項目にノート風 dashed ライン
- 全体フォントを Zen Maru Gothic に変更、角丸/ホバーで柔らかい雰囲気に
- iPad 用フォントをさらに底上げ
"""

import streamlit as st
import json
import requests
import base64
from datetime import datetime
from pathlib import Path

# ===== ページ設定 =====
st.set_page_config(page_title="RIA", page_icon="🌟", layout="wide", initial_sidebar_state="collapsed")

# ===== カラーパレット =====

SUBJECT_COLOR_MAP = {
    "国語":     {"primary": "#E91E63", "light": "#FCE4EC", "emoji": "📘"},
    "数学":     {"primary": "#1E88E5", "light": "#E3F2FD", "emoji": "📐"},
    "社会":     {"primary": "#FB8C00", "light": "#FFF3E0", "emoji": "🗺️"},
    "理科":     {"primary": "#43A047", "light": "#E8F5E9", "emoji": "🔬"},
    "英語":     {"primary": "#8E24AA", "light": "#F3E5F5", "emoji": "🌐"},
    "保健体育": {"primary": "#E53935", "light": "#FFEBEE", "emoji": "🏃"},
    "技術家庭": {"primary": "#00897B", "light": "#E0F2F1", "emoji": "🔧"},
    "技術":     {"primary": "#00897B", "light": "#E0F2F1", "emoji": "🔧"},
    "家庭":     {"primary": "#00897B", "light": "#E0F2F1", "emoji": "🍳"},
    "音楽":     {"primary": "#FFA000", "light": "#FFF8E1", "emoji": "🎵"},
    "美術":     {"primary": "#EC407A", "light": "#FCE4EC", "emoji": "🎨"},
}

def subject_color(name):
    name = str(name).strip()
    for key, val in SUBJECT_COLOR_MAP.items():
        if key in name:
            return val
    return {"primary": "#888", "light": "#f5f5f5", "emoji": "📚"}


# ===== スタイル =====
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700;900&display=swap');

    /* 全体フォント */
    .stApp, .stApp * {
        font-family: 'Zen Maru Gothic', 'Hiragino Sans', 'Yu Gothic', sans-serif !important;
    }

    /* ========== ベース（モバイル）========== */
    .test-card {
        background: linear-gradient(135deg, #ff6b9d 0%, #ee5a52 100%);
        color: white; border-radius: 20px; padding: 28px; text-align: center;
        box-shadow: 0 6px 24px rgba(238, 90, 82, 0.25);
    }
    .section-title { font-size: 22px; font-weight: 700; margin: 28px 0 12px 0; color: #2c3e50; }
    .section-title.big { font-size: 30px; margin-top: 36px; }

    .range-item {
        background: #fff8f8; padding: 12px 16px; border-radius: 12px;
        border-left: 4px solid #ff6b6b; margin: 8px 0;
    }
    .study-time-badge {
        background: #4a90e2; color: white; padding: 3px 12px; border-radius: 12px;
        font-size: 13px; font-weight: bold;
    }
    .cover-ph {
        background: linear-gradient(135deg, #e0e0e0, #c0c0c0); height: 180px;
        border-radius: 12px; display: flex; align-items: center; justify-content: center;
        color: #888; font-size: 13px;
    }
    .now-badge {
        text-align: right; color: #888; font-size: 13px;
        margin: -10px 0 10px 0;
    }

    /* ===== スケジュールカレンダー ===== */
    .calendar-scroll {
        display: flex; gap: 8px;
        overflow-x: auto; padding: 24px 4px 16px;
        -webkit-overflow-scrolling: touch;
        scroll-snap-type: x mandatory;
    }
    .calendar-scroll::-webkit-scrollbar { height: 6px; }
    .calendar-scroll::-webkit-scrollbar-thumb { background: #e0e0e0; border-radius: 3px; }
    .day-card {
        flex-shrink: 0; width: 88px; min-height: 130px;
        background: white; border-radius: 16px; padding: 10px 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        border: 2px solid #f0f0f0;
        scroll-snap-align: start;
        position: relative;
        transition: transform 0.2s;
    }
    .day-card:hover { transform: translateY(-2px); }
    .day-card.today {
        border-color: #4a90e2;
        background: linear-gradient(135deg, #e3f2fd, #fff);
        box-shadow: 0 6px 16px rgba(74, 144, 226, 0.25);
    }
    .day-card.test-day {
        border-color: #ff6b6b;
        background: linear-gradient(135deg, #ffe5e5, #fff);
        box-shadow: 0 6px 16px rgba(255, 107, 107, 0.2);
    }
    .day-card.past { opacity: 0.45; }
    .today-badge {
        position: absolute; top: -14px; left: 50%;
        transform: translateX(-50%);
        background: #4a90e2; color: white;
        font-size: 11px; font-weight: bold;
        padding: 3px 10px; border-radius: 10px;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(74, 144, 226, 0.4);
    }
    .day-num { font-size: 19px; font-weight: 700; color: #2c3e50; text-align: center; line-height: 1.1; }
    .day-wd { font-size: 12px; text-align: center; margin-bottom: 8px; }
    .chips { display: flex; flex-direction: column; gap: 3px; }
    .chip {
        font-size: 11px; padding: 3px 5px; border-radius: 8px;
        background: #f5f5f5; color: #666; text-align: center;
        font-weight: 500; line-height: 1.3;
    }
    .chip-test {
        background: #ff6b6b !important; color: white !important;
        font-weight: 700; border: none !important;
    }
    .chip-submit {
        background: #ffd54f !important; color: #5d4037 !important;
        font-weight: 700; border: none !important;
    }

    /* ===== ToDo カード ===== */
    .todo-card {
        border-radius: 16px; padding: 14px 18px; margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: all 0.2s;
        border-left: 6px solid #888;
    }
    .todo-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
    .todo-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .todo-content { flex: 1; }
    .todo-subj { font-size: 17px; font-weight: 700; margin-bottom: 4px; }
    .todo-task { font-size: 14px; color: #333; line-height: 1.5; }
    .todo-time {
        color: white; padding: 6px 12px; border-radius: 14px;
        font-size: 12px; font-weight: bold; white-space: nowrap;
    }

    /* ===== ポイントボックス ===== */
    .point-box, .point-box-blue {
        padding: 14px 18px; border-radius: 12px;
        margin: 8px 0 14px 0; line-height: 1.8;
    }
    .point-box { background: #fff8e1; border-left: 3px solid #f5c518; }
    .point-box-blue { background: #f0f7ff; border-left: 3px solid #4a90e2; }
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

    /* ===== TOC ===== */
    .toc-sect-title {
        font-size: 14px; font-weight: 700;
        color: #2c3e50; margin: 12px 0 4px 0;
    }
    .toc-sub {
        font-size: 13px; line-height: 1.7;
        padding: 10px 4px 10px 8px;
    }
    .toc-sub .toc-page { color: #888; font-size: 0.9em; }

    /* TOC 内の章 expander */
    .st-key-tb_toc div[data-testid="stExpander"] summary,
    .st-key-tb_toc div[data-testid="stExpander"] summary p {
        font-size: 14px !important;
    }
    .st-key-tb_toc div[data-testid="stExpander"] { margin: 4px 0; border-radius: 12px; }

    /* ノート風ライン: TOC 内の各 subsection 行に下線 */
    .st-key-tb_toc div[data-testid="stHorizontalBlock"] {
        border-bottom: 1px dashed #d8d8d8;
        align-items: center;
        margin-bottom: 0 !important;
    }
    .st-key-tb_toc div[data-testid="stHorizontalBlock"]:last-child {
        border-bottom: none;
    }

    /* 教科書カバー */
    .tb-cover-wrap { text-align: center; padding: 12px 0; }
    .tb-cover {
        width: 220px; max-width: 70%; border-radius: 14px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    .tb-cover:hover { transform: scale(1.04); }
    .tb-cover-hint { color: #888; font-size: 12px; margin-top: 10px; }

    /* ボタン基本 */
    div.stButton > button {
        min-height: 48px; font-size: 16px;
        border-radius: 14px !important;
        transition: all 0.2s;
        font-weight: 500;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    div[role="radiogroup"] { justify-content: center; }
    div[data-testid="stSegmentedControl"] { display: flex; justify-content: center; }

    /* ========== iPad / タブレット以上 (≥768px) ========== */
    @media (min-width: 768px) {
        .section-title { font-size: 28px; }
        .section-title.big { font-size: 38px; }
        .now-badge { font-size: 15px; }

        .day-card { width: 112px; min-height: 160px; padding: 14px 10px; }
        .day-num { font-size: 24px; }
        .day-wd { font-size: 14px; }
        .chip { font-size: 13px; padding: 4px 6px; }

        .todo-card { padding: 18px 22px; }
        .todo-subj { font-size: 20px; }
        .todo-task { font-size: 16px; }
        .todo-time { font-size: 14px; padding: 8px 14px; }

        .range-item { padding: 16px 20px; }
        .range-item strong { font-size: 18px; }
        .study-time-badge { font-size: 15px; padding: 4px 14px; }

        .point-box, .point-box-blue { padding: 20px 24px; }
        .point-box p, .point-box-blue p,
        .point-box li, .point-box-blue li {
            font-size: 17px !important; line-height: 1.9 !important;
        }
        .point-box h1, .point-box-blue h1,
        .point-box h2, .point-box-blue h2 {
            font-size: 23px !important; margin: 18px 0 8px 0 !important;
        }
        .point-box h3, .point-box-blue h3 { font-size: 19px !important; }

        .toc-sect-title { font-size: 17px; margin: 14px 0 6px; }
        .toc-sub { font-size: 16px; line-height: 1.9; padding: 12px 4px 12px 8px; }

        .st-key-tb_toc div[data-testid="stExpander"] summary,
        .st-key-tb_toc div[data-testid="stExpander"] summary p {
            font-size: 17px !important;
        }

        div[data-testid="stExpander"] summary { font-size: 18px; }
        div.stButton > button { font-size: 18px; min-height: 54px; }
        div[data-testid="stCheckbox"] label p { font-size: 16px; }

        .tb-cover { width: 240px; }
        .tb-cover-hint { font-size: 14px; }
    }

    /* ========== デスクトップ (≥1024px) ========== */
    @media (min-width: 1024px) {
        .point-box, .point-box-blue { padding: 22px 28px; }
        .point-box p, .point-box-blue p,
        .point-box li, .point-box-blue li {
            font-size: 18px !important;
        }
        .point-box h1, .point-box-blue h1,
        .point-box h2, .point-box-blue h2 {
            font-size: 25px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ===== 教科 × ジャンル定義 =====

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


def load_textbook(subject_key, genre_key):
    filename = f"{subject_key}_{genre_key}_textbook.json"
    local_path = DATA_DIR / filename
    if local_path.exists():
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    try:
        url = f"https://raw.githubusercontent.com/rebale-minobe/RIA/main/data/{filename}"
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
    st.markdown(
        f"<div class='{cls}'>\n\n{text}\n\n</div>",
        unsafe_allow_html=True
    )


# ===== スケジュール（テストまでの計画）=====

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
        if d.weekday() == 5:
            wd_color = "#4a90e2"
        elif d.weekday() == 6:
            wd_color = "#ff6b6b"
        else:
            wd_color = "#888"

        chips_html = ""
        for it in items:
            subj = it["subj"]
            ctype = it.get("type", "study")
            if ctype == "test":
                chips_html += '<div class="chip chip-test">TEST</div>'
            elif ctype == "submit":
                short = subj.replace("📝 ", "").replace("ワーク提出", "ワーク提出")
                chips_html += f'<div class="chip chip-submit">{short}</div>'
            else:
                color = subject_color(subj)
                chips_html += (
                    f'<div class="chip" style="'
                    f'background:{color["light"]}; '
                    f'color:{color["primary"]}; '
                    f'border:1px solid {color["primary"]};">{subj}</div>'
                )

        today_marker = '<div class="today-badge">👇 今日</div>' if is_today else ''
        days_html.append(
            f'<div class="{" ".join(classes)}">'
            f'{today_marker}'
            f'<div class="day-num">{d.month}/{d.day}</div>'
            f'<div class="day-wd" style="color:{wd_color};">({wd})</div>'
            f'<div class="chips">{chips_html}</div>'
            f'</div>'
        )

    return f'<div class="calendar-scroll">{"".join(days_html)}</div>'


# ===== ダミーデータ =====

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
    {"subject_name": "社会",  "task": "歴史 P105-130 教科書通読",   "duration": "60分", "done": False},
    {"subject_name": "数学",  "task": "1年範囲 P225-248 復習",       "duration": "30分", "done": False},
    {"subject_name": "国語",  "task": "漢字テスト範囲 10個",         "duration": "20分", "done": True},
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

# ===== 教科書を「タップで開く」処理（query_params 経由）=====
qp = st.query_params
if "open_tb" in qp:
    target = qp["open_tb"]
    if "__" in target:
        skey, gkey = target.split("__", 1)
        if skey in SUBJECTS and gkey in SUBJECTS[skey]["genres"]:
            st.session_state.selected_study = skey
            st.session_state.detail_subject = skey
            st.session_state.detail_genre = gkey
            st.session_state.detail_type = "textbook"
    del st.query_params["open_tb"]
    st.rerun()

# ===== ToDo 完了状態を session_state に保持 =====
if "todo_done" not in st.session_state:
    st.session_state.todo_done = {i: t["done"] for i, t in enumerate(TODO_TODAY)}

# ===== 現在日時 =====
st.markdown(
    f"<div class='now-badge'>🕐 {today.year}年{today.month}月{today.day}日"
    f"（{today_wd}）{today.strftime('%H:%M')}</div>",
    unsafe_allow_html=True
)

# ===== カレンダー（NEXT TESTの上）=====
st.markdown('<div class="section-title">📆 期末テストまでのスケジュール</div>', unsafe_allow_html=True)
st.markdown(render_calendar(STUDY_SCHEDULE, today), unsafe_allow_html=True)

# ===== NEXT TEST =====
st.markdown('<div class="section-title">⏳ NEXT TEST</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="test-card">
    <div style="font-size: 18px; opacity: 0.9;">{NEXT_TEST['name']} まで</div>
    <div style="display: flex; align-items: baseline; justify-content: center; gap: 10px; margin: 14px 0;">
        <span style="font-size: 72px; font-weight: 900; line-height: 1;">{days_until_test}</span>
        <span style="font-size: 28px; font-weight: 700;">日</span>
    </div>
    <div style="font-size: 13px; opacity: 0.85;">開始: {NEXT_TEST['start_date']}（{test_wd}）</div>
</div>
""", unsafe_allow_html=True)

# ===== TEST詳細 トグル =====
btn_label = "📋 TEST詳細を閉じる" if st.session_state.get("show_test_detail") else "📋 TEST詳細を見る"
if st.button(btn_label, key="toggle_test_detail", use_container_width=True):
    st.session_state["show_test_detail"] = not st.session_state.get("show_test_detail", False)

if st.session_state.get("show_test_detail"):
    total_hours = sum(s["study_hours"] for s in NEXT_TEST["subjects"])
    daily = total_hours / max(days_until_test, 1)
    st.markdown(
        f"**推奨勉強時間 合計: {total_hours} 時間**"
        f"（残り {days_until_test} 日 → 1日 約{daily:.1f}時間）"
    )
    for s in NEXT_TEST["subjects"]:
        col = subject_color(s['subject'])
        st.markdown(f"""
        <div class="range-item" style="border-left-color:{col['primary']}; background:{col['light']};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color:{col['primary']};">{col['emoji']} {s['subject']}</strong>
                <span class="study-time-badge" style="background:{col['primary']};">⏱ {s['study_hours']}h</span>
            </div>
            <div style="font-size: 13px; color: #666; margin-top: 4px;">
                📅 {s['date']} {s['time']}<br>📖 {s['range']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ===== To Do TODAY (カード式) =====
st.markdown('<div class="section-title">📌 To Do TODAY</div>', unsafe_allow_html=True)
done_count = sum(1 for v in st.session_state.todo_done.values() if v)
st.markdown(f"今日のタスク: **{done_count}/{len(TODO_TODAY)}** 完了 🎯")

for i, todo in enumerate(TODO_TODAY):
    is_done = st.session_state.todo_done.get(i, todo["done"])
    col = subject_color(todo["subject_name"])

    bg = col["light"] if not is_done else "#f5f5f5"
    text_deco = "line-through" if is_done else "none"
    opacity = "0.55" if is_done else "1"

    st.markdown(f"""
    <div class="todo-card" style="border-left-color:{col['primary']}; background:{bg}; opacity:{opacity};">
        <div class="todo-row">
            <div class="todo-content" style="text-decoration:{text_deco};">
                <div class="todo-subj" style="color:{col['primary']};">{col['emoji']} {todo['subject_name']}</div>
                <div class="todo-task">{todo['task']}</div>
            </div>
            <div class="todo-time" style="background:{col['primary']};">⏱ {todo['duration']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns([3, 1])
    with cols[1]:
        btn_label = "↩️ 戻す" if is_done else "✅ できた！"
        if st.button(btn_label, key=f"todo_btn_{i}", use_container_width=True):
            st.session_state.todo_done[i] = not is_done
            st.rerun()

st.caption("💡 To Do は RIA が自動生成（予定）")

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
                sel_gname = st.radio("ジャンル", gnames, horizontal=True, key=f"today_grad_{pn}")
                _, _, tdata = next(g for g in gtocs if g[1] == sel_gname)
            else:
                _, _, tdata = gtocs[0]

            chapters = tdata["textbook"]["chapters"]
            chapter_labels = [
                f"{c.get('chapter_number','').strip()} {c.get('title','').strip()}".strip()
                for c in chapters
            ]

            sel_ch = st.selectbox(
                "章", chapter_labels,
                index=None, placeholder="章を選択...",
                key=f"today_ch_{pn}", label_visibility="collapsed"
            )

            if sel_ch:
                ch_idx = chapter_labels.index(sel_ch)
                chap = chapters[ch_idx]
                sub_opts = []
                for sec in chap.get("sections", []):
                    for sub in sec.get("subsections", []):
                        sub_opts.append(f"{sub['title']} (p.{sub['page']})")

                if sub_opts:
                    sel_subs = st.multiselect(
                        "項目（複数選択可）", sub_opts,
                        placeholder="やった項目を選択...",
                        key=f"today_subs_{pn}", label_visibility="collapsed"
                    )

                    if sel_subs and st.button("✅ 記録する", key=f"today_rec_{pn}", use_container_width=True):
                        st.success(f"記録: {sel_ch} ／ {len(sel_subs)}項目")
        else:
            sr = st.text_input(
                "範囲", placeholder="今日やった範囲を入力",
                key=f"today_range_{pn}", label_visibility="collapsed"
            )
            if sr and st.button("✅ 記録する", key=f"today_rec_{pn}", use_container_width=True):
                st.success(f"記録: {sr}")

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

st.markdown('<div class="section-title big">📚 教科書/ワーク</div>', unsafe_allow_html=True)

subject_keys = list(SUBJECTS.keys())
subject_labels = [SUBJECTS[k]['name'] for k in subject_keys]

current_label = None
if st.session_state.get("selected_study") in SUBJECTS:
    cs = st.session_state.selected_study
    current_label = SUBJECTS[cs]['name']

selected_label = st.segmented_control(
    "教科", subject_labels,
    default=current_label,
    label_visibility="collapsed",
    key="subject_seg"
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
        sel_label = st.radio(
            "ジャンル", list(genre_display.keys()),
            horizontal=True, label_visibility="collapsed",
            key=f"genre_radio_{skey}"
        )
        gkey = genre_display[sel_label]
    else:
        gkey = genre_keys[0]
    ginfo = sinfo["genres"][gkey]
    data = load_textbook(skey, gkey)

    if data and data.get("textbook", {}).get("cover_image"):
        tb = data["textbook"]
        cover_path = DATA_DIR / tb["cover_image"]
        if cover_path.exists():
            with open(cover_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            # クリック可能カバー（query_params 経由で開く）
            st.markdown(f"""
            <div class="tb-cover-wrap">
                <a href="?open_tb={skey}__{gkey}" style="text-decoration:none;" target="_self">
                    <img src="data:image/jpeg;base64,{b64}" class="tb-cover" alt="教科書">
                </a>
                <div class="tb-cover-hint">👆 表紙をタップで目次を見る</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="cover-ph">📖 教科書 未登録</div>', unsafe_allow_html=True)
        st.caption("「教科書登録」ページで登録できます")

    if st.session_state.get("detail_type") == "textbook" and st.session_state.get("detail_genre") == gkey:
        ddata = load_textbook(st.session_state.detail_subject, st.session_state.detail_genre)
        if ddata:
            st.markdown("---")
            st.markdown(
                f"<div style='font-size:20px; font-weight:700; color:#2c3e50; margin: 8px 0 4px 0;'>"
                f"📄 目次 — {ddata['textbook'].get('name', '')}</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='font-size:13px; color:#888; margin-bottom:10px;'>"
                "章を開いて、項目の「💡」でポイントを見られます ✨</div>",
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
                                c1, c2 = st.columns([6, 1])
                                with c1:
                                    st.markdown(
                                        f"<div class='toc-sub'>　• {sub['title']} "
                                        f"<span class='toc-page'>(p.{sub['page']})</span></div>",
                                        unsafe_allow_html=True
                                    )
                                with c2:
                                    pt_key = f"pt_text_{sub['id']}"
                                    if st.button("💡", key=f"pt_{sub['id']}", help="ポイントを見る"):
                                        with st.spinner("生成中..."):
                                            st.session_state[pt_key] = generate_point(
                                                sub["title"],
                                                subject_name=sinfo['name'],
                                                genre_name=ginfo['name']
                                            )
                                pt_key = f"pt_text_{sub['id']}"
                                if st.session_state.get(pt_key):
                                    render_point_box(st.session_state[pt_key], color="yellow")

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | TOP ページ v0.8")
