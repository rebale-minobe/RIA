"""
RIA TOP ページ v0.6
更新点 (v0.6):
- 今日の時間割: 目次登録あり科目は「章 → 項目(複数選択)」UI
- ポイント生成: Anthropic API で実動作（中2向けの要点解説）
- 「📚 教科書/ワーク」見出しを拡大
- 目次フォント縮小（章expander含めて14px統一）
- 「明日の時間割（予習プレビュー）」→「明日の予習」
"""

import streamlit as st
import json
import requests
import base64
from datetime import datetime
from pathlib import Path

# ===== ページ設定 =====
st.set_page_config(page_title="RIA", page_icon="🌟", layout="wide", initial_sidebar_state="collapsed")

# ===== スタイル =====
st.markdown("""
<style>
    .ria-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 20px; border: 1px solid #f0f0f0;
    }
    .test-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white; border-radius: 16px; padding: 28px; text-align: center;
    }
    .section-title { font-size: 22px; font-weight: 700; margin: 24px 0 12px 0; color: #2c3e50; }
    .section-title.big { font-size: 30px; margin-top: 32px; }
    .range-item {
        background: #fff8f8; padding: 12px 16px; border-radius: 8px;
        border-left: 4px solid #ff6b6b; margin: 8px 0;
    }
    .study-time-badge {
        background: #4a90e2; color: white; padding: 2px 10px; border-radius: 10px;
        font-size: 13px; font-weight: bold;
    }
    .cover-ph {
        background: linear-gradient(135deg, #e0e0e0, #c0c0c0); height: 180px;
        border-radius: 8px; display: flex; align-items: center; justify-content: center;
        color: #888; font-size: 13px;
    }
    .now-badge {
        text-align: right; color: #888; font-size: 13px;
        margin: -10px 0 10px 0;
    }
    .point-box {
        background: #fff8e1; padding: 12px 16px; border-radius: 8px;
        margin: 6px 0 12px 0; font-size: 14px; line-height: 1.7;
        border-left: 3px solid #f5c518;
    }
    .point-box-blue {
        background: #f0f7ff; padding: 12px 16px; border-radius: 8px;
        margin: 8px 0; font-size: 14px; line-height: 1.7;
        border-left: 3px solid #4a90e2;
    }

    div.stButton > button { min-height: 48px; font-size: 16px; }
    div[role="radiogroup"] { justify-content: center; }
    div[data-testid="stSegmentedControl"] { display: flex; justify-content: center; }

    /* TOC コンテナ内の expander ラベルを 14px に縮小 */
    .st-key-tb_toc div[data-testid="stExpander"] summary,
    .st-key-tb_toc div[data-testid="stExpander"] summary p {
        font-size: 14px !important;
    }
    .st-key-tb_toc div[data-testid="stExpander"] {
        margin: 2px 0;
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
    """指定教科で目次登録済みのジャンル一覧を返す。"""
    if subject_key not in SUBJECTS:
        return []
    out = []
    for gk, ginfo in SUBJECTS[subject_key]["genres"].items():
        data = load_textbook(subject_key, gk)
        if data and data.get("textbook", {}).get("chapters"):
            out.append((gk, ginfo["name"], data))
    return out


def generate_point(title, subject_name, genre_name=""):
    """Anthropic API でポイント解説を生成（中2向け）。"""
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
                    f"3〜5個の箇条書きで簡潔に教えてください。\n"
                    f"・各項目は1〜2文以内\n"
                    f"・専門用語は分かりやすい言葉に置き換えて\n"
                    f"・親しみやすく、わくわくする口調で"
                )
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"⚠️ エラー: {e}"


# ===== ダミーデータ =====

NEXT_TEST = {
    "name": "1学期 期末テスト", "start_date": "2026-06-18",
    "subjects": [
        {"subject": "技術家庭", "date": "6/18(木)", "time": "9:00", "range": "教科書 P30-55", "study_hours": 2},
        {"subject": "国語", "date": "6/18(木)", "time": "9:45", "range": "漢字 + 文法 + 読解「故郷」", "study_hours": 5},
        {"subject": "社会", "date": "6/18(木)", "time": "10:45", "range": "歴史 P105-160", "study_hours": 8},
        {"subject": "保健体育", "date": "6/18(木)", "time": "11:45", "range": "教科書 P20-40", "study_hours": 2},
        {"subject": "数学", "date": "6/19(金)", "time": "9:00", "range": "1年範囲 + 文章題 + 連立方程式", "study_hours": 12},
        {"subject": "英語", "date": "6/19(金)", "time": "10:00", "range": "Unit 1-3 + 英作文", "study_hours": 3},
        {"subject": "理科", "date": "6/19(金)", "time": "10:55", "range": "化学変化 + 生物", "study_hours": 4},
    ]
}

TODO_TODAY = [
    {"subject": "🗺️ 社会", "task": "歴史 P105-130 教科書通読", "duration": "60分", "done": False},
    {"subject": "📐 数学", "task": "1年範囲 P225-248 復習", "duration": "30分", "done": False},
    {"subject": "📘 国語", "task": "漢字テスト範囲 10個", "duration": "20分", "done": True},
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
    <div style="font-size: 18px; opacity: 0.9;">{NEXT_TEST['name']} まで</div>
    <div style="display: flex; align-items: baseline; justify-content: center; gap: 10px; margin: 14px 0;">
        <span style="font-size: 72px; font-weight: 800; line-height: 1;">{days_until_test}</span>
        <span style="font-size: 28px; font-weight: 600;">日</span>
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
        st.markdown(f"""
        <div class="range-item">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong>{s['subject']}</strong>
                <span class="study-time-badge">⏱ {s['study_hours']}h</span>
            </div>
            <div style="font-size: 13px; color: #666; margin-top: 4px;">
                📅 {s['date']} {s['time']}<br>📖 {s['range']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ===== To Do TODAY =====
st.markdown('<div class="section-title">📌 To Do TODAY</div>', unsafe_allow_html=True)
done_count = sum(1 for t in TODO_TODAY if t["done"])
st.markdown(f"今日のタスク: **{done_count}/{len(TODO_TODAY)}** 完了")
for i, todo in enumerate(TODO_TODAY):
    st.checkbox(
        f"{todo['subject']} — {todo['task']}（{todo['duration']}）",
        value=todo["done"], key=f"todo_{i}"
    )
st.caption("💡 To Do は RIA が自動生成（予定）")

# ===== 今日の時間割 =====
st.markdown('<div class="section-title">📅 今日の時間割</div>', unsafe_allow_html=True)
for p in TODAY_TIMETABLE:
    pn = p['period']
    with st.expander(f"**{pn}**　{p['subject']}", expanded=False):
        skey = p.get("subject_key")
        gtocs = get_genres_with_toc(skey) if skey else []

        if gtocs:
            # 目次あり: ジャンル選択 → 章選択 → 項目複数選択
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
            # 目次なし: text_input フォールバック
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
    with st.expander(f"**{pn}**　{p['subject']}", expanded=False):
        st.markdown(f"📖 次回学習：**{p['next_chapter']}**（{p['page']}）")
        point_key = f"tm_point_text_{pn}"
        if st.button("💡 ポイントを見る", key=f"tm_point_{pn}", use_container_width=True):
            with st.spinner("ポイント生成中..."):
                st.session_state[point_key] = generate_point(p['next_chapter'], p['subject'])

        if st.session_state.get(point_key):
            st.markdown(
                f"<div class='point-box-blue'>{st.session_state[point_key]}</div>",
                unsafe_allow_html=True
            )

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
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<img src='data:image/jpeg;base64,{b64}' "
                f"style='width:220px;max-width:70%;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.15);'></div>",
                unsafe_allow_html=True
            )
        bc1, bc2, bc3 = st.columns([1, 2, 1])
        with bc2:
            if st.button("📖 開く", key=f"open_tb_{skey}_{gkey}", use_container_width=True):
                st.session_state.detail_subject = skey
                st.session_state.detail_genre = gkey
                st.session_state.detail_type = "textbook"
                st.rerun()
    else:
        st.markdown('<div class="cover-ph">📖 教科書 未登録</div>', unsafe_allow_html=True)
        st.caption("「教科書登録」ページで登録できます")

    if st.session_state.get("detail_type") == "textbook" and st.session_state.get("detail_genre") == gkey:
        ddata = load_textbook(st.session_state.detail_subject, st.session_state.detail_genre)
        if ddata:
            st.markdown("---")
            st.markdown(
                f"<div style='font-size:18px; font-weight:700; color:#2c3e50; margin: 8px 0 4px 0;'>"
                f"📄 目次 — {ddata['textbook'].get('name', '')}</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='font-size:12px; color:#888; margin-bottom:10px;'>"
                "章を開いて、項目の「💡」でポイントを見られます</div>",
                unsafe_allow_html=True
            )

            # TOC コンテナ（CSS で expander ラベルを縮小）
            with st.container(key="tb_toc"):
                for chapter in ddata["textbook"]["chapters"]:
                    ch_title = f"{chapter.get('chapter_number', '')} {chapter['title']}"
                    with st.expander(f"📖 {ch_title}"):
                        for section in chapter.get("sections", []):
                            if section.get("title"):
                                st.markdown(
                                    f"<div style='font-size:13px; font-weight:600; "
                                    f"color:#2c3e50; margin: 8px 0 4px 0;'>"
                                    f"{section['title']}</div>",
                                    unsafe_allow_html=True
                                )
                            for sub in section.get("subsections", []):
                                c1, c2 = st.columns([6, 1])
                                with c1:
                                    st.markdown(
                                        f"<div style='font-size:13px; line-height:1.8; "
                                        f"padding-left:8px;'>　• {sub['title']} "
                                        f"<span style='color:#888;'>(p.{sub['page']})</span></div>",
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
                                    st.markdown(
                                        f"<div class='point-box'>{st.session_state[pt_key]}</div>",
                                        unsafe_allow_html=True
                                    )

# ===== フッター =====
st.markdown("---")
st.caption("🌟 RIA | TOP ページ v0.6")
