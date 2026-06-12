"""理科ページ v2026-06-12.1"""
import streamlit as st
import requests
import io
import base64
import re
from collections import OrderedDict

st.set_page_config(page_title="理科 - RIA", page_icon="🔬", layout="wide")

RIKA_VERSION = "v2026-06-12.1"

GH_RAW = "https://raw.githubusercontent.com/rebale-minobe/RIA/main"
PRINT_XLSX_URL = f"{GH_RAW}/data/science_print_answers.xlsx"
PRINT_IMG_BASE = f"{GH_RAW}/data/science_prints"

# ========== CSS ==========
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
.wb-progress-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 600; margin: 12px 0 4px; }
.soc-section-title { font-size: 22px; font-weight: 700; margin: 8px 0 4px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="soc-section-title">🔬 理科</div>', unsafe_allow_html=True)


# ========== データ読み込み ==========
@st.cache_data(ttl=300)
def load_print_sheets():
    """science_print_answers.xlsx を読み込み、シート名→データのdictを返す"""
    try:
        from openpyxl import load_workbook
        r = requests.get(PRINT_XLSX_URL, timeout=10)
        if r.status_code != 200:
            return {}
        wb = load_workbook(io.BytesIO(r.content), data_only=True)
        result = OrderedDict()
        for sn in wb.sheetnames:
            ws = wb[sn]
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 3:
                continue
            unit_title = ""
            if rows[0] and len(rows[0]) >= 2 and rows[0][0] == "unit_title":
                unit_title = rows[0][1] or ""
            header = [str(c).strip() if c else "" for c in rows[1]]
            data = []
            for r_ in rows[2:]:
                if not r_ or all(c is None for c in r_):
                    continue
                d = {}
                for i, h in enumerate(header):
                    d[h] = r_[i] if i < len(r_) and r_[i] is not None else ""
                data.append(d)
            result[sn] = {"unit_title": unit_title, "questions": data}
        return result
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return {}


@st.cache_data(ttl=300)
def fetch_print_image(sheet_name, section):
    """プリント画像を取得しbase64で返す（例: 02-06_A_1.jpg）"""
    url = f"{PRINT_IMG_BASE}/{sheet_name}_{section}.jpg"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except Exception:
        pass
    return None


def parse_sheet_label(sheet_name):
    """02-06_A -> (学年, プリント番号, 表裏, ラベル)"""
    m = re.match(r"(\d+)-(\d+)_([AB])", sheet_name)
    if m:
        grade, no, side = m.group(1), m.group(2), m.group(3)
        side_label = "基本" if side == "A" else "発展"
        return grade, no, side, side_label
    return None, None, None, None


sheets = load_print_sheets()

if not sheets:
    st.info("📚 プリントデータがまだありません。science_print_answers.xlsx をアップロードしてください。")
    st.caption(f"理科ページ {RIKA_VERSION}")
    st.stop()


# ========== 積上プリント ==========
st.markdown('<div class="soc-section-title" style="margin-top:24px;">📚 積上プリント</div>', unsafe_allow_html=True)

sheet_names = list(sheets.keys())
def _sort_key(sn):
    g, no, side, _ = parse_sheet_label(sn)
    return (int(no) if no else 999, side or "Z")
sheet_names.sort(key=_sort_key)

pill_labels = {}
for sn in sheet_names:
    g, no, side, side_label = parse_sheet_label(sn)
    pill_labels[f"{no}{side}"] = sn

pill_options = list(pill_labels.keys())
selected_pill = st.segmented_control(
    "プリント選択", pill_options,
    default=pill_options[0], key="rika_print_pill"
)
if not selected_pill:
    selected_pill = pill_options[0]

selected_sheet = pill_labels[selected_pill]
sheet_data = sheets[selected_sheet]
unit_title = sheet_data["unit_title"]
questions = sheet_data["questions"]

g, no, side, side_label = parse_sheet_label(selected_sheet)
st.markdown(
    f"<div style='text-align:center;margin:12px 0 4px;'>"
    f"<span style='display:inline-block;background:#E8F4FD;color:#0A7;"
    f"padding:4px 16px;border-radius:20px;font-size:14px;font-weight:700;'>"
    f"🔬 理科{g}年・プリント{no}（{side_label}）</span></div>",
    unsafe_allow_html=True
)
st.markdown(
    f"<div style='text-align:center;font-size:20px;font-weight:800;color:#1c1c1e;margin:6px 0 14px;'>"
    f"{unit_title}</div>",
    unsafe_allow_html=True
)

sections = []
for q in questions:
    s = q.get("section", "")
    if s and s not in sections:
        sections.append(s)


# ========== フラッシュカード本体（セクションごと） ==========
@st.fragment
def render_section_flashcard(sheet_name, section, sec_questions):
    _section_title = sec_questions[0].get("section_title", "") if sec_questions else ""

    b64 = fetch_print_image(sheet_name, section)
    if b64:
        st.markdown(
            f"<div style='text-align:center;margin:10px 0;'>"
            f"<img src='data:image/jpeg;base64,{b64}' "
            f"style='width:100%;max-width:720px;border-radius:12px;"
            f"box-shadow:0 4px 16px rgba(0,0,0,0.1);'></div>",
            unsafe_allow_html=True
        )
    else:
        st.warning(f"画像が見つかりません: {sheet_name}_{section}.jpg")

    _total = len(sec_questions)
    _start_key = f"rika_started_{sheet_name}_{section}"
    _idx_key = f"rika_idx_{sheet_name}_{section}"

    if not st.session_state.get(_start_key):
        st.markdown(
            f"<div class='wb-flashcard' style='text-align:center;'>"
            f"<div style='font-size:40px;margin-bottom:6px;'>📖</div>"
            f"<div style='font-size:26px;font-weight:800;color:#FF9500;margin-bottom:8px;'>Let's Start!!</div>"
            f"<div style='font-size:15px;color:#8E8E93;'>{_section_title}　全 {_total} 問</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("NEXT ▶", type="primary", use_container_width=True,
                     key=f"rika_start_btn_{sheet_name}_{section}"):
            st.session_state[_start_key] = True
            st.session_state[_idx_key] = 0
            st.rerun(scope="fragment")
        return

    if _idx_key not in st.session_state:
        st.session_state[_idx_key] = 0
    _cur_pos = max(0, min(st.session_state[_idx_key], _total - 1))
    st.session_state[_idx_key] = _cur_pos
    _cur_q = sec_questions[_cur_pos]

    st.markdown(
        f"<div class='wb-progress-row'><span>問題 <b>{_cur_pos+1}</b> / {_total}</span></div>",
        unsafe_allow_html=True
    )
    st.progress((_cur_pos + 1) / _total)

    _q_label = _cur_q.get("q_label", "")
    _answer = _cur_q.get("answer", "")
    _yomi = _cur_q.get("answer_yomi", "")
    _meta = " ／ ".join(filter(None, [_section_title, f"問 {_q_label}"]))

    st.markdown(
        f"<div class='wb-flashcard'>"
        f"<div style='text-align:center;margin-bottom:10px;'>"
        f"<div class='wb-fc-meta'>{_meta}</div>"
        f"</div>"
        f"<div class='wb-fc-q'>{_q_label}</div>"
        f"<div class='wb-fc-divider'></div>"
        f"<div class='wb-fc-a-area'><div style='text-align:center;'>"
        f"<div style='font-size:38px;font-weight:700;color:#1c1c1e;line-height:1.4;"
        f"word-break:break-word;font-family:\"Hiragino Mincho ProN\",\"Yu Mincho\",\"游明朝\",Georgia,serif;'>"
        f"{_answer}</div>"
        + (f"<div style='font-size:16px;color:#8E8E93;font-weight:500;margin-top:4px;'>({_yomi})</div>"
           if _yomi else "")
        + "</div></div></div>",
        unsafe_allow_html=True
    )

    with st.container(key=f"rika_nav_{sheet_name}_{section}"):
        _nc = st.columns([1, 3])
        with _nc[0]:
            if st.button("◀", key=f"rika_prev_{sheet_name}_{section}_{_cur_pos}",
                         disabled=(_cur_pos == 0), use_container_width=True):
                st.session_state[_idx_key] = _cur_pos - 1
                st.rerun(scope="fragment")
        with _nc[1]:
            if _cur_pos < _total - 1:
                if st.button("NEXT ▶", key=f"rika_next_{sheet_name}_{section}_{_cur_pos}",
                             type="primary", use_container_width=True):
                    st.session_state[_idx_key] = _cur_pos + 1
                    st.rerun(scope="fragment")
            else:
                if st.button("🎉 完了！もう一度", key=f"rika_done_{sheet_name}_{section}",
                             use_container_width=True):
                    st.session_state[_start_key] = False
                    st.session_state[_idx_key] = 0
                    st.rerun(scope="fragment")


for section in sections:
    sec_questions = [q for q in questions if str(q.get("section", "")) == str(section)]
    if not sec_questions:
        continue
    _sec_title = sec_questions[0].get("section_title", f"セクション{section}")
    st.markdown(
        f"<div style='font-size:17px;font-weight:700;color:#0A7;margin:24px 0 4px;"
        f"border-left:4px solid #0A7;padding-left:10px;'>"
        f"【{section}】{_sec_title}</div>",
        unsafe_allow_html=True
    )
    render_section_flashcard(selected_sheet, section, sec_questions)


# ========== 追加アップロード機能 ==========
st.markdown("---")
st.markdown('<div class="soc-section-title">➕ 問題を追加する</div>', unsafe_allow_html=True)
st.caption("新しいプリントの問題画像と解答画像をアップロードできます")

with st.expander("📤 アップロード", expanded=False):
    up_sheet = st.text_input("プリント名（例: 02-08_A）", key="rika_up_sheet", placeholder="02-08_A")
    up_section = st.text_input("セクション番号（例: 1）", key="rika_up_section", placeholder="1")
    up_q_img = st.file_uploader("問題画像（JPG）", type=["jpg", "jpeg", "png"], key="rika_up_q_img")
    up_a_img = st.file_uploader("解答画像（JPG）", type=["jpg", "jpeg", "png"], key="rika_up_a_img")
    if up_q_img:
        st.image(up_q_img, caption="問題画像プレビュー", width=400)
    if up_a_img:
        st.image(up_a_img, caption="解答画像プレビュー", width=400)
    if st.button("💾 保存（準備中）", type="primary", key="rika_up_save"):
        if not up_sheet or not up_section:
            st.error("プリント名とセクション番号を入力してください")
        elif not up_q_img:
            st.error("問題画像をアップロードしてください")
        else:
            st.info(
                f"📝 アップロード予定:\n\n"
                f"- 問題画像: `{up_sheet}_{up_section}.jpg`\n"
                f"- 保存先: `data/science_prints/`\n\n"
                f"※ GitHub保存機能は次のステップで実装します"
            )

# ========== バージョン表示 ==========
st.markdown("---")
st.markdown(
    f"<div style='text-align:right;font-size:11px;color:#C7C7CC;'>"
    f"4_🔬_理科.py　{RIKA_VERSION}</div>",
    unsafe_allow_html=True
)
