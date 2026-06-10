"""社会ページ v2026-06-09.2"""
SOCIAL_VERSION = "v2026-06-09.2"
import streamlit as st
import json
import csv
from io import StringIO
import requests
from shared.ui import render_subject_page
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="社会 - RIA", page_icon="🗺️", layout="wide")
render_subject_page("social", "社会", "🗺️")

# ========== alp / alm インポート
try:
    from modules import answer_log_pivot as alp
    ALP_AVAILABLE = True
except Exception:
    ALP_AVAILABLE = False

try:
    from modules import answer_log_manager as alm
    ALM_AVAILABLE = True
except Exception:
    ALM_AVAILABLE = False

# ========== JST ヘルパー
_JST = timezone(timedelta(hours=9))
def _now_jst():
    return datetime.now(_JST).replace(tzinfo=None)

# ========== GitHub CSV ロード
GITHUB_RAW = "https://raw.githubusercontent.com/rebale-minobe/RIA/main"

# ========== ワーク読み込み（Excelから）
_GENRE_SHEET_MAP = {
    "history": "歴史", "geography": "地理", "civics": "公民",
}

@st.cache_data(ttl=300)
def _load_workbook_excel():
    import openpyxl, io
    url = f"{GITHUB_RAW}/data/social_data.xlsx"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
    except Exception:
        pass
    return None

def load_workbook_answers_social(genre_key="history"):
    wb = _load_workbook_excel()
    if wb is None:
        return None
    genre_jp = _GENRE_SHEET_MAP.get(genre_key, "歴史")
    sheet_name = f"ワーク{genre_jp}_解答"
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
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
                "page_number": page_num, "workbook_ref": wb_ref or "",
                "chapter_title": ch_title or "", "lesson_title": lesson_title or "",
                "sections": []
            }
        pg = pages_dict[page_num]
        sec = next((s for s in pg["sections"]
                    if s["code"] == str(sec_code or "") and s.get("textbook_ref") == (tb_ref or "")), None)
        if sec is None:
            sec = {"code": str(sec_code) if sec_code else "", "name": str(sec_name) if sec_name else "",
                   "textbook_ref": tb_ref or "", "groups": []}
            pg["sections"].append(sec)
        grp = next((g for g in sec["groups"] if g["label"] == (group_label or "")), None)
        if grp is None:
            grp = {"label": group_label or "", "answers": []}
            sec["groups"].append(grp)
        grp["answers"].append({"q": str(q), "a": str(a),
                                "note": str(note) if note else None,
                                "context": str(context) if context else None})
    if not pages_dict:
        return None
    return {"workbook_title": f"{genre_jp}ワーク", "pages": list(pages_dict.values())}

def flatten_wb_questions(page):
    flat = []
    for section in page["sections"]:
        for group in section["groups"]:
            for ans in group["answers"]:
                flat.append({
                    "page_number": page["page_number"],
                    "lesson_title": page.get("lesson_title", ""),
                    "chapter_title": page.get("chapter_title", ""),
                    "workbook_ref": page.get("workbook_ref", ""),
                    "section_code": section["code"],
                    "section_name": section["name"],
                    "textbook_ref": section.get("textbook_ref", ""),
                    "group_label": group.get("label", ""),
                    "q": ans["q"], "a": ans["a"],
                    "note": ans.get("note"), "context": ans.get("context"),
                })
    return flat

# ========== フラッシュカード CSS
st.markdown("""
<style>
.wb-flashcard {
    background: white; border-radius: 18px; padding: 20px 24px 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 2px solid #FF9500; margin: 12px 0 16px;
}
.wb-fc-meta { font-size: 11px; color: #8E8E93; font-weight: 600; letter-spacing: 0.04em; }
.wb-fc-lesson { font-size: 14px; font-weight: 700; color: #1c1c1e; margin-top: 2px; }
.wb-fc-q { font-size: 30px; font-weight: 800; color: #FF9500; text-align: center; line-height: 1.0; margin: 10px 0 6px; }
.wb-fc-divider { border-top: 1px dashed #e5e5ea; margin: 14px -10px; }
.wb-fc-a-area { text-align: center; min-height: 70px; display: flex; align-items: center; justify-content: center; padding: 12px 0; }
.wb-fc-a-shown { font-size: 38px; font-weight: 700; color: #1c1c1e; line-height: 1.4; word-break: break-word; }
.wb-progress-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 600; margin: 12px 0 4px; }
.st-key-soc_wb_nav button {
    font-size: 20px !important; min-height: 60px !important; font-weight: 700 !important;
    border: none !important; border-radius: 16px !important;
}
.st-key-soc_wb_nav [data-testid="stHorizontalBlock"] > div:nth-child(1) button { background: #E5E5EA !important; color: #3a3a3c !important; }
.st-key-soc_wb_nav [data-testid="stHorizontalBlock"] > div:nth-child(2) button { background: white !important; color: #FF3B30 !important; border: 2px solid #FF3B30 !important; }
.st-key-soc_wb_nav [data-testid="stHorizontalBlock"] > div:nth-child(3) button { background: #E8F8EE !important; color: #1a8a3c !important; border: 2px solid #34C759 !important; }
.st-key-soc_wb_nav [data-testid="stHorizontalBlock"] > div:nth-child(4) button { background: linear-gradient(160deg,#007AFF 0%,#0055d4 100%) !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# ========== 📋 ワーク（フラッシュカード）セクション
st.markdown("---")
st.subheader("📋 ワーク解答（フラッシュカード）")

_wb_data = load_workbook_answers_social("history")

if not _wb_data or not _wb_data.get("pages"):
    st.info("ワークデータが見つかりません（social_data.xlsx / ワーク歴史_解答 シート）")
else:
    _wb_pages = _wb_data["pages"]
    _page_labels = [f"P.{p['page_number']}" for p in _wb_pages]

    _sel_page = st.pills("📄 ページを選択", _page_labels,
                         key="soc_wb_page_sel", default=_page_labels[0])
    if not _sel_page:
        _sel_page = _page_labels[0]
    _page_idx = _page_labels.index(_sel_page)
    _page = _wb_pages[_page_idx]
    _page_num = _page["page_number"]

    st.markdown(
        f"<div style='font-size:16px;font-weight:600;margin:6px 0 14px;color:#1d1d1f;'>"
        f"📖 {_page.get('lesson_title','')}</div>",
        unsafe_allow_html=True
    )

    _questions = flatten_wb_questions(_page)
    _total = len(_questions)

    if _total == 0:
        st.warning("このページに問題が登録されていません")
    else:
        # Let's Start!! 画面
        _start_key = f"soc_wb_started_{_sel_page}"
        _last_key = f"soc_wb_last_page"
        if st.session_state.get(_last_key) != _sel_page:
            st.session_state[_start_key] = False
            st.session_state[_last_key] = _sel_page

        if not st.session_state.get(_start_key, False):
            st.markdown(f"""
            <div style='background:white; border:2px solid #FF9500; border-radius:20px;
                        padding:48px 24px; text-align:center; margin:16px 0;
                        box-shadow:0 4px 20px rgba(0,0,0,.06);'>
                <div style='font-size:52px; margin-bottom:12px;'>📖</div>
                <div style='font-size:28px; font-weight:800; color:#FF9500; margin-bottom:8px;'>Let's Start!!</div>
                <div style='font-size:15px; color:#8E8E93;'>{_page.get('lesson_title','')}　全 {_total} 問</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("NEXT ▶", type="primary", use_container_width=True, key=f"soc_wb_start_{_sel_page}"):
                st.session_state[_start_key] = True
                st.rerun()
        else:
            # モード
            _mode_key = f"soc_wb_mode_{_page_num}"
            _mode = st.session_state.get(_mode_key, "normal")
            if _mode == "normal":
                _active = list(range(_total))
            else:
                _active = [i for i in range(_total)
                           if st.session_state.get(f"soc_wb_result_{_page_num}_{i}") == "batsu"]
                if not _active:
                    st.session_state[_mode_key] = "normal"
                    _active = list(range(_total))
                    _mode = "normal"

            _n_active = len(_active)
            _idx_key = f"soc_wb_idx_{_page_num}_{_mode}"
            if _idx_key not in st.session_state:
                st.session_state[_idx_key] = 0
            _cur_pos = max(0, min(st.session_state[_idx_key], _n_active - 1))
            st.session_state[_idx_key] = _cur_pos
            _orig_idx = _active[_cur_pos]
            _cur_q = _questions[_orig_idx]
            _result = st.session_state.get(f"soc_wb_result_{_page_num}_{_orig_idx}")

            if _mode == "retest":
                st.markdown("<div style='display:inline-block;background:#FF6B00;color:white;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:700;margin-bottom:8px;'>🔄 再テストモード</div>", unsafe_allow_html=True)

            # 進捗
            _wrong = sum(1 for i in range(_total) if st.session_state.get(f"soc_wb_result_{_page_num}_{i}") == "batsu")
            _wrong_label = f"❌ {_wrong} 問" if _wrong else ""
            st.markdown(f"<div class='wb-progress-row'><span>問題 <b>{_cur_pos+1}</b> / {_n_active}</span><span style='color:#FF3B30;font-weight:700;'>{_wrong_label}</span></div>", unsafe_allow_html=True)
            st.progress((_cur_pos + 1) / _n_active)

            # フラッシュカード
            _border = "#FF3B30" if _result == "batsu" else "#FF9500"
            _meta = " ／ ".join(filter(None, [
                f"{_cur_q.get('section_code','')} {_cur_q.get('section_name','')}".strip(),
                _cur_q.get("group_label",""), _cur_q.get("workbook_ref","")
            ]))
            st.markdown(f"""
            <div class='wb-flashcard' style='border-color:{_border};'>
                <div style='text-align:center;margin-bottom:10px;'>
                    <div class='wb-fc-meta'>{_meta}</div>
                    <div class='wb-fc-lesson'>{_cur_q.get('lesson_title','')}</div>
                </div>
                <div class='wb-fc-q'>{_cur_q['q']}</div>
                <div class='wb-fc-divider'></div>
                <div class='wb-fc-a-area'>
                    <div class='wb-fc-a-shown'>{_cur_q['a']}</div>
                </div>
                {'<div style="text-align:center;margin-top:8px;font-size:13px;color:#FF3B30;font-weight:700;">❌ もう一度</div>' if _result == "batsu" else ''}
            </div>
            """, unsafe_allow_html=True)

            if _cur_q.get("note"): st.caption(f"※ {_cur_q['note']}")
            if _cur_q.get("context"): st.caption(f"💭 {_cur_q['context']}")

            # ナビボタン（◀ ❌ 💡 NEXT▶）
            with st.container(key="soc_wb_nav"):
                _nc = st.columns([1, 1.2, 1.2, 1.6])
                with _nc[0]:
                    if st.button("◀", key=f"soc_wb_prev_{_page_num}_{_orig_idx}",
                                 disabled=(_cur_pos == 0), use_container_width=True):
                        st.session_state[_idx_key] = _cur_pos - 1
                        st.rerun()
                with _nc[1]:
                    _batsu_label = "❌ 消す" if _result == "batsu" else "❌"
                    if st.button(_batsu_label, key=f"soc_wb_batsu_{_page_num}_{_orig_idx}", use_container_width=True):
                        if _result == "batsu":
                            st.session_state.pop(f"soc_wb_result_{_page_num}_{_orig_idx}", None)
                        else:
                            st.session_state[f"soc_wb_result_{_page_num}_{_orig_idx}"] = "batsu"
                            if ALP_AVAILABLE:
                                try:
                                    _qd = _cur_q.copy()
                                    _qd["page_num"] = _page_num
                                    _qd["q_label"] = _cur_q["q"]
                                    _qd["answer"] = _cur_q["a"]
                                    alp.append_pivot_log("social", _qd, "batsu")
                                except Exception:
                                    pass
                        st.rerun()
                with _nc[2]:
                    _exp_key = f"soc_wb_exp_{_page_num}_{_orig_idx}"
                    _exp_label = "💡 隠す" if st.session_state.get(_exp_key) else "💡"
                    if st.button(_exp_label, key=f"soc_wb_exp_btn_{_page_num}_{_orig_idx}", use_container_width=True):
                        if st.session_state.get(_exp_key):
                            del st.session_state[_exp_key]
                        else:
                            with st.spinner("解説生成中..."):
                                st.session_state[_exp_key] = generate_workbook_explanation(_cur_q, "社会")
                        st.rerun()
                with _nc[3]:
                    if _cur_pos < _n_active - 1:
                        if st.button("NEXT ▶", key=f"soc_wb_next_{_page_num}_{_orig_idx}",
                                     use_container_width=True, help="次の問題"):
                            if _result != "batsu" and ALP_AVAILABLE:
                                try:
                                    _qd = _cur_q.copy()
                                    _qd["page_num"] = _page_num
                                    _qd["q_label"] = _cur_q["q"]
                                    _qd["answer"] = _cur_q["a"]
                                    alp.append_pivot_log("social", _qd, "maru")
                                except Exception:
                                    pass
                            st.session_state[_idx_key] = _cur_pos + 1
                            st.rerun()
                    else:
                        st.button("最後", key=f"soc_wb_next_{_page_num}_{_orig_idx}",
                                  use_container_width=True, disabled=True)

            # 解説表示
            if st.session_state.get(f"soc_wb_exp_{_page_num}_{_orig_idx}"):
                st.markdown(
                    "<div style='background:#FFF8E1;border-left:4px solid #FFCC00;padding:14px 16px;"
                    "border-radius:10px;margin-top:12px;font-size:15px;line-height:1.8;font-weight:500;'>"
                    "💡 " + st.session_state[f"soc_wb_exp_{_page_num}_{_orig_idx}"] + "</div>",
                    unsafe_allow_html=True
                )

            # ページ完了
            if _cur_pos == _n_active - 1:
                _wrong_indices = [i for i in range(_total)
                                  if st.session_state.get(f"soc_wb_result_{_page_num}_{i}") == "batsu"]
                st.markdown("---")
                if _wrong_indices:
                    st.warning(f"❌ {len(_wrong_indices)} 問にマークあり")
                    if _mode == "normal":
                        if st.button(f"🔄 ×の {len(_wrong_indices)} 問で再テスト",
                                     use_container_width=True, type="primary", key=f"soc_wb_retest_{_page_num}"):
                            st.session_state[_mode_key] = "retest"
                            st.session_state[f"soc_wb_idx_{_page_num}_retest"] = 0
                            st.rerun()
                    else:
                        if st.button("↩️ 通常モードに戻る", use_container_width=True, key=f"soc_wb_back_{_page_num}"):
                            st.session_state[_mode_key] = "normal"
                            st.rerun()
                else:
                    st.success("🎉 全問チェック完了！")
                if st.button("🗑️ このページの×をリセット", key=f"soc_wb_reset_{_page_num}", use_container_width=True):
                    for i in range(_total):
                        st.session_state.pop(f"soc_wb_result_{_page_num}_{i}", None)
                        st.session_state.pop(f"soc_wb_exp_{_page_num}_{i}", None)
                    st.session_state[_mode_key] = "normal"
                    st.session_state[f"soc_wb_idx_{_page_num}_normal"] = 0
                    st.rerun()

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

# タイトルボタンを左寄せにするCSS
st.markdown("""
<style>
div[data-testid="stButton"] > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding-left: 20px !important;
}
</style>
""", unsafe_allow_html=True)

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
                # ★ pivot CSV に再TEST結果を記録
                if ALP_AVAILABLE:
                    try:
                        alp.append_pivot_log("social", tp_current, result_val)
                    except Exception:
                        pass
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


# ========== 📊 CSVデータビューワー
st.markdown("---")
st.subheader("📊 学習データ（answer_log_social_pivot）")

@st.cache_data(ttl=10)
def _load_csv_for_view():
    rows = _load_social_pivot_csv()
    if not rows:
        return [], []
    # 日付列を抽出
    date_cols = [c for c in rows[0].keys()
                 if c.endswith('_maru') or c.endswith('_batsu')]
    return rows, date_cols

csv_rows, date_cols = _load_csv_for_view()

if not csv_rows:
    st.info("CSVデータがありません")
else:
    # page_num の一覧（セグメント用）
    page_nums = sorted(set(r['page_num'] for r in csv_rows), key=lambda x: int(x))
    page_labels = [f"P.{p}" for p in page_nums]

    selected_page = st.segmented_control(
        "ページを選択", page_labels,
        default=page_labels[0],
        key="csv_view_page"
    )
    if not selected_page:
        selected_page = page_labels[0]

    sel_p_num = selected_page.replace("P.", "")
    page_rows = [r for r in csv_rows if r['page_num'] == sel_p_num]

    if not page_rows:
        st.info("このページのデータはありません")
    else:
        # ヘッダー行を構築（batsu列のみ表示）
        batsu_cols = [c for c in date_cols if c.endswith('_batsu')]
        col_widths = [1, 3] + [1] * len(batsu_cols)

        # ❌データがある行のみフィルタ
        batsu_rows = [r for r in page_rows if any(r.get(c,'') for c in batsu_cols)]
        if not batsu_rows:
            st.success("🎉 このページに❌はありません！")
        else:
            # ヘッダー
            h_cols = st.columns(col_widths)
            h_cols[0].markdown("**問**")
            h_cols[1].markdown("**答え**")
            for i, dc in enumerate(batsu_cols):
                date_part = dc.replace('_batsu','')[-5:]
                h_cols[2 + i].markdown(f"**{date_part}**<br>**❌**", unsafe_allow_html=True)

            st.divider()

            for row in batsu_rows:
                r_cols = st.columns(col_widths)
                r_cols[0].markdown(f"<span style='font-size:12px;'>{row.get('q_label','')}</span>", unsafe_allow_html=True)
                r_cols[1].markdown(f"<span style='font-size:13px;'>{row.get('answer','')}</span>", unsafe_allow_html=True)
                for i, dc in enumerate(batsu_cols):
                    val = row.get(dc, '')
                    if val:
                        r_cols[2 + i].markdown(
                            f"<span style='font-weight:700;color:#FF3B30;font-size:14px;'>{val}</span>",
                            unsafe_allow_html=True
                        )
                    else:
                        r_cols[2 + i].markdown("—")

# ========== 🔧 デバッグ（開発用）==========
with st.expander("🔧 デバッグ"):
    st.write("**pivot log テスト**")
    try:
        from modules import answer_log_pivot as alp
        ALP_OK = True
        st.success("✅ answer_log_pivot インポート成功")
    except Exception as e:
        ALP_OK = False
        st.error(f"❌ インポート失敗: {e}")

    if ALP_OK:
        if st.button("▶ テストデータを書き込む（P.2 地図①）"):
            test_q = {
                "page_num": 2,
                "section_code": "地図",
                "q_label": "①",
                "answer": "イ",
            }
            try:
                ok = alp.append_pivot_log("social", test_q, "maru")
                if ok:
                    st.success("✅ 書き込み成功！60秒後に表に反映")
                else:
                    st.error("❌ 書き込み失敗（GitHub API エラー）")
            except Exception as e:
                st.error(f"❌ エラー: {e}")
