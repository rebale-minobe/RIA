"""社会ページ v5 - answer_log_social_pivot.csv を直接参照"""
import streamlit as st
import json
import csv
from io import StringIO
import requests
from shared.ui import render_subject_page
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="社会 - RIA", page_icon="🗺️", layout="wide")
render_subject_page("social", "社会", "🗺️")

# ========== JST ヘルパー
_JST = timezone(timedelta(hours=9))
def _now_jst():
    return datetime.now(_JST).replace(tzinfo=None)

# ========== GitHub CSV ロード
GITHUB_RAW = "https://raw.githubusercontent.com/rebale-minobe/RIA/main"

@st.cache_data(ttl=60)
def _load_social_pivot_csv():
    """answer_log_social_pivot.csv を GitHub から読み込む"""
    try:
        url = f"{GITHUB_RAW}/data/answer_log_social_pivot.csv"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.text.strip():
            reader = csv.DictReader(StringIO(r.text))
            return list(reader)
    except Exception:
        pass
    return []

def _get_social_batsu_questions():
    """新CSV形式から batsu 問題を抽出"""
    rows = _load_social_pivot_csv()
    if not rows:
        return []
    
    result = []
    for row in rows:
        # 日付カラム（date_maru, date_batsu）から最新結果を判定
        latest_result = None
        latest_date = None
        
        for col_name in row.keys():
            if col_name.endswith('_maru') or col_name.endswith('_batsu'):
                value = row[col_name]
                if not value:
                    continue
                
                try:
                    count = int(value)
                    if count > 0:
                        date = col_name.replace('_maru', '').replace('_batsu', '')
                        if latest_date is None or date > latest_date:
                            latest_date = date
                            latest_result = 'maru' if col_name.endswith('_maru') else 'batsu'
                except ValueError:
                    pass
        
        # batsu が最新結果の問題のみを追加
        if latest_result == 'batsu':
            q_data = {
                "page_num": row.get("page_num", ""),
                "chapter_title": row.get("chapter_title", ""),
                "lesson_title": row.get("lesson_title", ""),
                "workbook_ref": row.get("workbook_ref", ""),
                "section_code": row.get("section_code", ""),
                "q_label": row.get("q_label", ""),
                "q": row.get("q_label", ""),
                "a": row.get("answer", ""),
                "answer": row.get("answer", ""),
                "subject_name": "社会",
                "subject_key": "social",
                "genre_name": "歴史",
                "genre_key": "history",
                "section_name": row.get("chapter_title", ""),
            }
            result.append(q_data)
    
    return result

# CSV から全問題数を事前計算（各タイトルごと）
@st.cache_data(ttl=60)
def _get_title_total_counts():
    """各タイトルの全問題数を CSV から計算"""
    from collections import defaultdict
    rows = _load_social_pivot_csv()
    if not rows:
        return {}
    
    title_counts = defaultdict(int)
    for row in rows:
        lesson_title = row.get('lesson_title', '')
        if lesson_title:
            title_counts[lesson_title] += 1
    
    return dict(title_counts)

# 各タイトルの最新TEST日を取得
@st.cache_data(ttl=60)
def _get_title_latest_dates():
    """各タイトルの最新TEST日（YYYY-MM-DD）をCSVから取得"""
    rows = _load_social_pivot_csv()
    if not rows:
        return {}
    
    title_dates = {}
    for row in rows:
        lesson_title = row.get('lesson_title', '')
        if not lesson_title:
            continue
        for col_name in row.keys():
            if col_name.endswith('_maru') or col_name.endswith('_batsu'):
                if row[col_name]:
                    date = col_name.replace('_maru', '').replace('_batsu', '')
                    current = title_dates.get(lesson_title, '')
                    if date > current:
                        title_dates[lesson_title] = date
    return title_dates

# ========== 教科定義（TOP と同じ）
SUBJECTS = {
    "social": {"name": "社会", "emoji": "🗺️", "genres": {
        "history": {"name": "歴史", "emoji": "📜"},
        "geography": {"name": "地理", "emoji": "🌏"},
        "civics": {"name": "公民", "emoji": "⚖️"},
    }},
}

def subject_color(name):
    """TOP と同じ色定義"""
    SUBJECT_COLOR_MAP = {
        "社会": {"primary": "#FF9500", "light": "#FFF4E5", "emoji": "🗺️"},
    }
    name = str(name).strip()
    for key, val in SUBJECT_COLOR_MAP.items():
        if key in name:
            return val
    return {"primary": "#8E8E93", "light": "#F2F2F7", "emoji": "📚"}

# ========== AI 4択問題生成（TOP と同じ）
def _generate_quiz(q_data: dict) -> dict | None:
    """AI に4択問題を生成させる"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))
        lesson  = q_data.get("lesson_title", "")
        answer  = q_data.get("a", "")
        subject = q_data.get("subject_name", "社会")
        genre   = q_data.get("genre_name", "歴史")
        
        prompt = (
            f"中学2年生の{subject}（{genre}）の単元「{lesson}」に関する問題を1問作ってください。\n"
            f"正解は「{answer}」です。\n"
            + (f"正解の読み仮名：「{q_data.get('answer_yomi', '')}」\n" if q_data.get('answer_yomi') else "")
            + f"\n【ルール】\n"
            f"- 必ずこの単元・テーマの文脈で出題する（他の単元の知識は不要）\n"
            f"- 問題文は1文で、明確に問う\n"
            f"- 選択肢は4つ（正解1つ＋ダミー3つ）\n"
            f"- ダミーはこの単元に登場する似た語句・人物・地名から選ぶ\n"
            f"- 各選択肢には読み仮名（ふりがな・ひらがな）を必ず付ける\n"
            f"  （カタカナ語はyomiを空文字にする。記号・アルファベットのみもyomiを空文字）\n"
            f"  （正解「{answer}」のyomiは必ず「{q_data.get('answer_yomi', '')}」を使う）\n"
            f"- JSONのみ出力（説明不要）\n\n"
            f"出力フォーマット:\n"
            f'{{\n'
            f'  "question": "問題文",\n'
            f'  "choices": [\n'
            f'    {{"text": "選択肢A", "yomi": "せんたくしえー"}},\n'
            f'    {{"text": "選択肢B", "yomi": ""}},\n'
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
        return None

def generate_workbook_explanation(question_data, subject_name="社会"):
    """TOP と同じ解説生成（Claude API）"""
    try:
        from anthropic import Anthropic
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ""
        client = Anthropic(api_key=api_key)
        lesson = question_data.get("lesson_title", "")
        q = question_data.get("q", "")
        a = question_data.get("a", "")
        prompt = (
            f"中学{subject_name}の「{lesson}」という単元に関する次の問題について、\n"
            f"わかりやすく（中学生が理解できるレベルで）解説してください。\n\n"
            f"【問題】{q}\n【答え】{a}\n\n"
            f"- マークダウン記号や見出しは使わない、ふつうの文章で\n"
            f"- 前置きは不要、いきなり解説から"
        )
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {"role": "system", "content": "あなたは中学生に分かりやすく教えるのが得意な先生です。"},
                {"role": "user", "content": prompt},
            ],
        )
        return msg.content[0].text
    except Exception:
        return ""

# ========== ワーク再TEST セクション
st.markdown("---")
st.subheader("🔄 ワーク再TEST")
st.caption("誤答問題を4択で復習")

social_batsu = _get_social_batsu_questions()

if not social_batsu:
    st.info("📚 ワークで問題を解いて記録を作りましょう！")
    st.stop()

# ========== 問題リストから教科でフィルタ
social_questions = [q for q in social_batsu if q.get("subject_key", "") == "social"]

if not social_questions:
    st.success("🎉 全問3回連続正解達成！完璧です！")
    st.stop()

# ========== タイトルでグループ化
from collections import defaultdict
titles_dict = defaultdict(list)
title_order = []  # 出現順を保持

for q in social_questions:
    lesson_title = q.get("lesson_title", "")
    workbook_ref = q.get("workbook_ref", "")
    if lesson_title not in titles_dict:
        title_order.append(lesson_title)
    titles_dict[lesson_title].append(q)

# ========== タイトル選択 UI
st.markdown("### 📖 タイトルを選択")

# CSV から全問題数と最新TEST日を取得
title_total_counts = _get_title_total_counts()
title_latest_dates = _get_title_latest_dates()

# タイトル一覧をボタンで表示
selected_title = None
for title in title_order:
    problems = titles_dict[title]
    maru_count = sum(1 for p in problems if st.session_state.get(f"social_result_{id(p)}", None) == "maru")
    batsu_count = len(problems) - maru_count
    total_count_csv = title_total_counts.get(title, len(problems))  # CSV から取得した全問題数
    
    # バッジ表示
    if batsu_count == 0:
        badge = "🟢"  # 全問正解
    elif maru_count > 0:
        badge = "🟡"  # 部分正解
    else:
        badge = "🔴"  # 未解答

    label = f"{badge} {title} 本誌 {problems[0].get('workbook_ref', '')}"
    # 分子 = batsu問題数（CSVに登録されたバツの数）、分母 = CSV全問題数
    batsu_count_csv = len(problems)  # titles_dict は batsu のみなので全部がバツ
    progress = f"{batsu_count_csv}/{total_count_csv}"
    
    col1, col2 = st.columns([10, 2])
    with col1:
        if st.button(label, use_container_width=True, key=f"select_title_{title}"):
            selected_title = title
            st.session_state["selected_social_title"] = title
            st.rerun()
    with col2:
        latest_date = title_latest_dates.get(title, '')
        date_str = f"<span style='font-size:11px; color:#8E8E93;'>{latest_date}</span>" if latest_date else ""
        st.markdown(
            f"<div style='text-align:right; font-weight:700; color:#007AFF; margin-top:8px;'>"
            f"{progress}&nbsp;&nbsp;{date_str}</div>",
            unsafe_allow_html=True
        )

# 以前選択したタイトルを復元
if "selected_social_title" not in st.session_state and title_order:
    st.session_state["selected_social_title"] = title_order[0]

selected_title = st.session_state.get("selected_social_title", title_order[0] if title_order else None)

if not selected_title:
    st.stop()

st.divider()

# ========== 選択されたタイトルの問題のみをフィルタ
selected_questions = titles_dict[selected_title]

# ========== UI 状態管理
tp_idx_key = f"social_tp_idx_{selected_title}"
if tp_idx_key not in st.session_state:
    st.session_state[tp_idx_key] = 0

tp_total = len(selected_questions)
tp_pos = max(0, min(st.session_state[tp_idx_key], tp_total - 1))
st.session_state[tp_idx_key] = tp_pos

tp_current = selected_questions[tp_pos]

# ========== 進捗表示（TOP と同じ）
tp_correct = sum(1 for i in range(tp_total)
                if st.session_state.get(f"social_result_{id(selected_questions[i])}", None) == "maru")
tp_wrong   = sum(1 for i in range(tp_total)
                if st.session_state.get(f"social_result_{id(selected_questions[i])}", None) == "batsu")

st.markdown(f"""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
    <span style='font-size:18px; font-weight:700; color:#1c1c1e;'>
        問題 <b>{tp_pos + 1}</b> / {tp_total}
    </span>
    <span style='display:flex; gap:16px;'>
        <span style='color:#007AFF; font-weight:700;'>⭕ {tp_correct}</span>
        <span style='color:#FF3B30; font-weight:700;'>❌ {tp_wrong}</span>
    </span>
</div>
""", unsafe_allow_html=True)
st.progress((tp_pos + 1) / tp_total)

st.divider()

# ========== 教科バッジ
subj_name  = tp_current.get("subject_name", "社会")
genre_name = tp_current.get("genre_name", "歴史")
subj_col   = subject_color(subj_name)
subject_badge_html = (
    f'<div style="display:inline-block; background:{subj_col["light"]}; '
    f'color:{subj_col["primary"]}; padding:4px 14px; border-radius:14px; '
    f'font-size:13px; font-weight:700; margin-bottom:6px;">'
    f'{subj_col["emoji"]} {subj_name}'
    + (f' / {genre_name}' if genre_name else "")
    + "</div>"
)

# ========== AI クイズ生成
quiz_key = f"social_quiz_{selected_title}_{tp_pos}_{tp_current.get('q','')}"
if quiz_key not in st.session_state:
    with st.spinner("AI が問題を生成中..."):
        quiz = _generate_quiz(tp_current)
        st.session_state[quiz_key] = quiz
quiz = st.session_state.get(quiz_key)

tp_result = st.session_state.get(f"social_result_{selected_title}_{tp_pos}")

# ========== 問題表示（TOP と同じ フラッシュカード UI）
meta_parts = []
if tp_current.get("section_code"):
    meta_parts.append(f"{tp_current['section_code']} {tp_current.get('section_name','')}")
if tp_current.get("workbook_ref"):
    meta_parts.append(tp_current["workbook_ref"])

if quiz:
    st.markdown(f"""
    <div style='border:2px solid #FF9500; border-radius:14px; padding:24px; 
                background:white;'>
        <div style='margin-bottom:16px;'>
            {subject_badge_html}
            <div style='font-size:13px; color:#8E8E93; margin-top:8px; font-weight:500;'>
                {" ／ ".join(meta_parts)}
            </div>
            <div style='font-size:14px; font-weight:700; color:#1c1c1e; margin-top:4px;'>
                {tp_current.get("lesson_title","")}
            </div>
        </div>
        <div style='border-top:1px solid #E5E5EA; padding-top:16px; 
                    font-size:18px; font-weight:700; color:#1c1c1e; line-height:1.6;'>
            {quiz["question"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    selected    = st.session_state.get(f"social_selected_{selected_title}_{tp_pos}", "")
    correct_ans = quiz.get("answer", "")

    # 選択肢CSS（TOP と同じ）
    _div_base = (
        "width:100%; text-align:center; padding:14px 20px; "
        "border-radius:14px; margin:8px 0; font-size:17px; font-weight:700; "
        "line-height:1.4; box-sizing:border-box; "
        "font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;"
    )

    if tp_result:
        # 回答済み：HTML div で正誤をカラー表示（TOP と同じ）
        html = ""
        for ch in quiz["choices"]:
            ch_text = ch["text"] if isinstance(ch, dict) else str(ch)
            ch_yomi = ch.get("yomi", "") if isinstance(ch, dict) else ""
            is_correct  = ch_text == correct_ans
            is_selected = ch_text == selected
            yomi_html = (f"<br><span style='font-size:13px;font-weight:500;opacity:0.65;'>{ch_yomi}</span>"
                         if ch_yomi else "")
            if is_correct:
                s = _div_base + "background:#E5F8EE; border:2px solid #34C759; color:#1a8a3c;"
                lbl = "⭕ " + ch_text + yomi_html
            elif is_selected:
                s = _div_base + "background:#FFE5E2; border:2px solid #FF3B30; color:#c0392b;"
                lbl = "❌ " + ch_text + yomi_html
            else:
                s = _div_base + "background:#F9F9F9; border:1px solid #E5E5EA; color:#8E8E93;"
                lbl = ch_text + yomi_html
            html += "<div style=\"" + s + "\">" + lbl + "</div>"
        st.markdown(html, unsafe_allow_html=True)
        
        # 解説表示
        expl_key = f"social_explain_{tp_pos}"
        if st.session_state.get(expl_key):
            expl_s = (
                "background:#FFF8E1; border-left:4px solid #FFCC00; "
                "padding:14px 16px; border-radius:10px; margin-top:12px; "
                "font-size:15px; line-height:1.8; font-weight:500; "
                "font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
            )
            st.markdown(
                "<div style=\"" + expl_s + "\">💡 " + st.session_state[expl_key] + "</div>",
                unsafe_allow_html=True
            )
    else:
        # 未回答：1列×4行（TOP と同じ）
        for i, ch in enumerate(quiz["choices"]):
            ch_text = ch["text"] if isinstance(ch, dict) else str(ch)
            ch_yomi = ch.get("yomi", "") if isinstance(ch, dict) else ""
            # ラベルをフォーマット（改行で下に表示）
            if ch_yomi:
                btn_label = f"{ch_text}\n（{ch_yomi}）"
            else:
                btn_label = ch_text
            if st.button(btn_label, key=f"social_choice_{selected_title}_{tp_pos}_{i}",
                         use_container_width=True):
                st.session_state[f"social_selected_{selected_title}_{tp_pos}"] = ch_text
                result_val = "maru" if ch_text == correct_ans else "batsu"
                st.session_state[f"social_result_{selected_title}_{tp_pos}"] = result_val
                st.rerun()

# ========== ナビゲーション（TOP と同じ 5列）
st.markdown("")
nav_c = st.columns([1, 2, 1, 2, 1])

with nav_c[0]:
    if st.button("◀", key=f"social_prev_{selected_title}_{tp_pos}",
                 disabled=(tp_pos == 0), use_container_width=True):
        st.session_state[tp_idx_key] = tp_pos - 1
        st.rerun()

with nav_c[2]:
    explain_key = f"social_explain_{selected_title}_{tp_pos}"
    expl_label = "💡 非表示" if st.session_state.get(explain_key) else "💡"
    if st.button(expl_label, key=explain_key + "_btn",
                 use_container_width=True, help="解説を見る/隠す"):
        if st.session_state.get(explain_key):
            del st.session_state[explain_key]
        else:
            with st.spinner("解説生成中..."):
                st.session_state[explain_key] = (
                    generate_workbook_explanation(tp_current, subj_name)
                )
        st.rerun()

with nav_c[4]:
    if tp_pos < tp_total - 1:
        btn_label = "NEXT ▶" if tp_result else "スキップ ▶"
        btn_type  = "primary" if tp_result else "secondary"
        if st.button(btn_label, key=f"social_next_{selected_title}_{tp_pos}",
                     use_container_width=True, type=btn_type):
            st.session_state[tp_idx_key] = tp_pos + 1
            st.rerun()
    else:
        if tp_result:
            st.button("完了 ✓", key=f"social_next_{selected_title}_{tp_pos}",
                      use_container_width=True, disabled=True)

# ========== 全問完了
if tp_pos == tp_total - 1 and tp_result is not None:
    st.markdown("---")
    st.success(f"✅ {selected_title} {tp_total}問 再TEST完了！🎉")
    if st.button("📖 タイトル一覧に戻る", use_container_width=True):
        st.session_state.pop("selected_social_title", None)
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

