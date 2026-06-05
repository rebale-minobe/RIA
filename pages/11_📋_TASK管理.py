"""
RIA TASK管理ページ v1.0
- イベントTASK（AI自動生成）
- 定期TASK
- 自由TASK
- カレンダーへの日付割り当て → TOP反映
"""
import streamlit as st
import json
import requests
import base64
from datetime import datetime, timedelta

st.set_page_config(page_title="TASK管理 - RIA", page_icon="📋", layout="wide")

# ===== gh helper（app.pyと同じ設定） =====
OWNER  = "rebale-minobe"
REPO   = "RIA"
BRANCH = "main"

def _get_token():
    for key in ["GITHUB_PAT","github_pat","GH_TOKEN","gh_token","GITHUB_TOKEN","github_token"]:
        try:
            val = st.secrets.get(key)
            if val: return val
        except Exception:
            pass
    return ""

def _headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _api_url(path):
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"

def _get_sha(path):
    try:
        r = requests.get(_api_url(path) + f"?ref={BRANCH}", headers=_headers(), timeout=10)
        if r.status_code == 200:
            return r.json().get("sha")
    except Exception:
        pass
    return None

def gh_get_json(path):
    headers = {**_headers(), "Accept": "application/vnd.github.v3.raw"}
    try:
        r = requests.get(_api_url(path) + f"?ref={BRANCH}", headers=headers, timeout=10)
        if r.status_code == 200 and r.text.strip():
            return json.loads(r.text)
    except Exception:
        pass
    return None

def gh_put_json(path, data, message):
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    b64 = base64.b64encode(content).decode("ascii")
    sha = _get_sha(path)
    body = {"message": message, "content": b64, "branch": BRANCH}
    if sha: body["sha"] = sha
    r = requests.put(_api_url(path), headers=_headers(), json=body, timeout=30)
    if r.status_code == 409:
        body["sha"] = _get_sha(path)
        r = requests.put(_api_url(path), headers=_headers(), json=body, timeout=30)
    return r.status_code in (200, 201)

# ===== データ読み込み =====
@st.cache_data(ttl=30)
def load_tasks():
    data = gh_get_json("data/tasks.json")
    return data if data else {"tasks": []}

@st.cache_data(ttl=30)
def load_task_schedule():
    data = gh_get_json("data/task_schedule.json")
    return data if data else {"schedule": {}}

def save_tasks(data):
    load_tasks.clear()
    return gh_put_json("data/tasks.json", data, "Update tasks.json")

def save_task_schedule(data):
    load_task_schedule.clear()
    return gh_put_json("data/task_schedule.json", data, "Update task_schedule.json")

# ===== NEXT_TEST（app.pyと同期） =====
# 勉強時間の正確な計算
# 平日: 2h / 土日: 5h  / 6/3(水)〜6/17(月)
_STUDY_START    = datetime(2026, 6, 3)
_TEST_DATE      = datetime(2026, 6, 18)
_STUDY_DAYS     = (_TEST_DATE - _STUDY_START).days  # 15日
_WEEKDAY_HOURS  = 2
_WEEKEND_HOURS  = 5

# 実際の合計時間を計算
_TOTAL_HOURS = 0
_d = _STUDY_START
while _d < _TEST_DATE:
    _TOTAL_HOURS += _WEEKEND_HOURS if _d.weekday() >= 5 else _WEEKDAY_HOURS
    _d += timedelta(days=1)
# → 平日11日×2h + 土日4日×5h = 42h

# 教科別配分（重要度・範囲量・テスト日ベース）
_RATIO = {
    "数学":     0.28,  # 12h - 範囲最多・思考問題あり
    "社会":     0.22,  # 9h  - 4教材（教科書・資料集・プリント・ワーク）
    "国語":     0.19,  # 8h  - 聞き取り・漢字・文法・読解の多岐にわたる範囲
    "英語":     0.12,  # 5h  - Round1-8+英作文
    "理科":     0.12,  # 5h  - 積み上げプリント+2範囲
    "技術家庭": 0.05,  # 2h  - 技術・家庭の両分野
    "保健体育": 0.02,  # 1h  - 用語暗記中心
}

def _calc_hours(subj):
    return max(1, round(_TOTAL_HOURS * _RATIO.get(subj, 0.05)))

NEXT_TEST = {
    "name": "1学期 期末テスト",
    "start_date": "2026-06-18",
    "study_start": "2026-06-03",
    "study_days":  _STUDY_DAYS,
    "total_hours": _TOTAL_HOURS,
    "subjects": [
        {
            "subject": "技術家庭", "date": "6/18(木) 1校時",
            "study_hours": _calc_hours("技術家庭"),
            "range_detail": {
                "技術 ワーク・ノートC": "P2-6",
                "家庭 教科書": "P234-247, P264-267, P270-273, P280-281",
                "家庭 ワーク・ノート衣生活・住生活": "P36-38, P40-44",
                "家庭 消費生活・環境": "P3-14",
            },
            "point": "教科書の太字や学習ノートの内容を確認。授業で特においさえた内容を重点確認",
            "submission": "振り返りカード（試験前最後の授業日）",
        },
        {
            "subject": "国語", "date": "6/18(木) 2校時",
            "study_hours": _calc_hours("国語"),
            "range_detail": {
                "国語I": "「見えないだけ」「アイスプラネット」「枕草子」「クマゼミが増加の原因を探る」",
                "国語II": "教科書P308-310",
                "漢字": "P4-39（P29除く）",
                "文法": "文法プリント①〜⑤",
                "熟語": "熟語プリント⑤",
                "ワーク": "P4-39（P29除く）、P41-42",
            },
            "point": "放送による聞き取り試験あり。ノート・学習プリント（小テスト）をよく見直す。学んだことを自分の言葉で説明できるように。ワークで問題形式に慣れる",
            "submission": "ワーク提出 6/18(木)、ノート国語I・IIは授業中に指示",
        },
        {
            "subject": "社会", "date": "6/18(木) 3校時",
            "study_hours": _calc_hours("社会"),
            "range_detail": {
                "教科書 [歴史]": "P105-160",
                "資料集": "P80-115",
                "プリント": "No.1-15",
                "ワーク": "P2-23",
            },
            "point": "教科書を何回も読む。基本知識を確認してからワークを解く。ノート整理と思考力問題にも取り組む",
            "submission": "ノート提出（日程は再度連絡）",
        },
        {
            "subject": "保健体育", "date": "6/18(木) 4校時",
            "study_hours": _calc_hours("保健体育"),
            "range_detail": {
                "体育 器械運動": "教科書P30-41",
                "体育 陸上競技": "教科書P60-61, P74-85",
                "体育理論": "スポーツが心身および社会性に及ぼす効果 / スポーツの学び方 / スポーツの安全な行い方（教科書P74-79）",
            },
            "point": "教科書・オリエンテーション資料・授業で扱った内容を復習。技能の名称やポイントを確認",
            "submission": "なし",
        },
        {
            "subject": "数学", "date": "6/19(金) 1校時",
            "study_hours": _calc_hours("数学"),
            "range_detail": {
                "1年 教科書": "P225-248",
                "1年 ワーク": "P134-141",
                "2年 教科書": "P11-34",
                "2年 ワーク": "P4-27",
                "持ち物": "定規が必要",
            },
            "point": "解答は授業で教わった通りの書き方で。教科書・ノート・ワーク・プリントをよく復習。提出あり",
            "submission": "ノートとワーク提出（試験日までの近い日、詳細は授業で提示）",
        },
        {
            "subject": "英語", "date": "6/19(金) 2校時",
            "study_hours": _calc_hours("英語"),
            "range_detail": {
                "英作文ノート": "全範囲",
                "教科書 Round1": "Unit1-8",
                "教科書 Round2": "Unit1-5",
                "文法": "①過去形p.11 ②未来形p.13,37 ③when/if p.33 ④動名詞p.21 ⑤その他p.17,23,27,61",
                "Daily Life": "p.18, 69",
                "基礎の教科": "p.2-5, 18-19, 22-27, 30-31, 42-43",
            },
            "point": "聞き取り・選択・英作文の3形式あり。5Rワークを繰り返し。英作文ノートで発想力を養う。時間配分を意識",
            "submission": "英作文ノート提出（試験日）",
        },
        {
            "subject": "理科", "date": "6/19(金) 3校時",
            "study_hours": _calc_hours("理科"),
            "range_detail": {
                "1年 教科書": "p161-189",
                "2年 教科書": "p4-32",
                "2年 地学": "p68-79",
                "積み上げ": "No.12",
            },
            "point": "積み上げプリントを繰り返しやる。化学反応式・生物の図と用語をセットで覚える",
            "submission": "試験当日の帰りの学活でノートと積み上げを提出",
        },
    ]
}

JP_WD = ["月","火","水","木","金","土","日"]
SUBJECT_COLOR = {
    "国語":     {"primary":"#FF2D55","light":"#FFE5EC","emoji":"📘"},
    "数学":     {"primary":"#007AFF","light":"#E5F1FF","emoji":"📐"},
    "社会":     {"primary":"#FF9500","light":"#FFF4E5","emoji":"🗺️"},
    "理科":     {"primary":"#34C759","light":"#E8F8EE","emoji":"🔬"},
    "英語":     {"primary":"#AF52DE","light":"#F5EBFB","emoji":"🌐"},
    "保健体育": {"primary":"#FF3B30","light":"#FFE8E6","emoji":"🏃"},
    "技術家庭": {"primary":"#5AC8FA","light":"#E8F7FE","emoji":"🔧"},
}
def subj_color(name):
    for k, v in SUBJECT_COLOR.items():
        if k in name: return v
    return {"primary":"#8E8E93","light":"#F2F2F7","emoji":"📚"}

# ===== AI タスク生成 =====
def generate_tasks_ai(subject_info: dict, test_date_str: str) -> list:
    """教科の詳細情報からAIが具体的なタスクを生成"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY",""))

        subject    = subject_info["subject"]
        study_hours = subject_info["study_hours"]
        range_detail = subject_info.get("range_detail", {})
        point        = subject_info.get("point", "")
        submission   = subject_info.get("submission", "なし")

        # 範囲を箇条書きに整形
        range_text = "\n".join([f"  - {k}: {v}" for k, v in range_detail.items()])

        prompt = (
            f"中学2年生の【{subject}】期末テスト対策の勉強タスクを生成してください。\n\n"
            f"テスト日: {test_date_str}\n"
            f"合計勉強時間の目安: {study_hours}時間\n\n"
            f"【テスト範囲（詳細）】\n{range_text}\n\n"
            f"【先生からのポイント】\n{point}\n\n"
            f"【提出物】{submission}\n\n"
            f"【タスク生成ルール】\n"
            f"- 範囲の全教材（教科書・資料集・プリント・ワーク）を網羅する\n"
            f"- 1タスクは具体的で小さく（例:「教科書P105-120 通読」「ワークP2-7を解く」）\n"
            f"- 提出物がある場合は提出物タスクも含める\n"
            f"- duration_minは20〜60分の整数\n"
            f"- 合計時間が {study_hours*60}分 に近くなるよう調整\n"
            f"- 難易度順に並べる（基礎→応用の順）\n"
            f"- JSONのみ出力（説明不要）\n\n"
            f"出力: {{\"tasks\": [{{\"title\":\"タスク名\","
            f"\"duration_min\":30,\"note\":\"補足\"}},...]}}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "中学生の勉強タスクをJSONで生成してください。"},
                {"role": "user",   "content": prompt}
            ]
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("tasks", []) if isinstance(data, dict) else []
    except Exception as e:
        st.error(f"AI生成エラー: {e}")
        return []

# ===== スタイル =====
st.markdown("""
<style>
    .stApp {
        font-family: -apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;
        background: #fafafa;
    }
    .task-card {
        background: white; border-radius: 14px; padding: 14px 16px;
        margin: 8px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 4px solid #ccc;
    }
    .task-title { font-size: 16px; font-weight: 700; color: #1c1c1e; }
    .task-meta  { font-size: 13px; color: #8E8E93; margin-top: 4px; }
    .task-date  { font-size: 13px; font-weight: 600; color: #007AFF; }
    .section-title {
        font-size: 22px; font-weight: 700; margin: 24px 0 12px 0; color: #1c1c1e;
    }
    div.stButton > button {
        border-radius: 12px !important; font-weight: 600; min-height: 44px;
    }
</style>
""", unsafe_allow_html=True)

# ===== ページタイトル =====
st.markdown('<div class="section-title">📋 TASK管理</div>', unsafe_allow_html=True)

today = datetime.now()
test_date = datetime.strptime(NEXT_TEST["start_date"], "%Y-%m-%d")
days_left = (test_date - today).days

st.markdown(
    f'<div style="background:linear-gradient(135deg,#FF3B30,#FF2D55);color:white;'
    f'border-radius:14px;padding:14px 20px;margin-bottom:16px;">'
    f'⏳ {NEXT_TEST["name"]} まで <b style="font-size:24px;">{days_left}</b> 日</div>',
    unsafe_allow_html=True
)

# 勉強時間サマリー
_c1, _c2, _c3 = st.columns(3)
with _c1:
    st.metric("勉強開始〜テスト", f"{_STUDY_DAYS}日間")
with _c2:
    st.metric("合計勉強時間", f"{_TOTAL_HOURS}時間",
              help=f"平日{_WEEKDAY_HOURS}h × 11日 ＋ 土日{_WEEKEND_HOURS}h × 4日")
with _c3:
    _elapsed = (today - _STUDY_START).days
    _elapsed = max(0, min(_elapsed, _STUDY_DAYS))
    st.metric("経過", f"{_elapsed}日目 / {_STUDY_DAYS}日")

# ===== タブ =====
tab1, tab2, tab3, tab4 = st.tabs(["📝 テスト対策TASK", "🔁 定期TASK", "✏️ 自由TASK", "📅 スケジュール"])

tasks_data    = load_tasks()
schedule_data = load_task_schedule()

# ===== TAB1: テスト対策TASK =====
with tab1:
    st.markdown("### テスト範囲からAIがタスクを自動生成します")

    for subj_info in NEXT_TEST["subjects"]:
        subj  = subj_info["subject"]
        col   = subj_color(subj)
        hours = subj_info["study_hours"]

        # 範囲サマリー表示
        range_summary = " / ".join([f"{k}: {v}" for k, v in subj_info.get("range_detail",{}).items()])
        with st.expander(
            f"{col['emoji']} {subj}　{subj_info['date']}　"
            f"目安: {hours}h（{_STUDY_DAYS}日間で）",
            expanded=False
        ):
            if subj_info.get("point"):
                st.info(f"💡 {subj_info['point']}")
            if subj_info.get("submission") and subj_info["submission"] != "なし":
                st.warning(f"📝 提出物: {subj_info['submission']}")
            # 既存タスクを表示
            existing = [t for t in tasks_data["tasks"]
                       if t.get("type") == "test" and t.get("subject") == subj]
            if existing:
                st.markdown("**登録済みタスク:**")
                for t in existing:
                    date_str = t.get("due_date","未割当")
                    done_mark = "✅" if t.get("done") else "⬜"
                    st.markdown(
                        f'<div class="task-card" style="border-left-color:{col["primary"]};">'
                        f'<div class="task-title">{done_mark} {t["title"]}</div>'
                        f'<div class="task-meta">⏱ {t["duration_min"]}分　'
                        f'<span class="task-date">📅 {date_str}</span></div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                if st.button("🗑️ リセットして再生成", key=f"reset_{subj}"):
                    tasks_data["tasks"] = [t for t in tasks_data["tasks"]
                                          if not (t.get("type")=="test" and t.get("subject")==subj)]
                    save_tasks(tasks_data)
                    st.rerun()
            else:
                if st.button(f"✨ AIでタスクを生成", key=f"gen_{subj}", type="primary"):
                    with st.spinner(f"{subj}のタスクを生成中..."):
                        new_tasks = generate_tasks_ai(subj_info, NEXT_TEST["start_date"])
                        if new_tasks:
                            import uuid
                            for t in new_tasks:
                                tasks_data["tasks"].append({
                                    "id":           str(uuid.uuid4())[:8],
                                    "type":         "test",
                                    "subject":      subj,
                                    "title":        t.get("title",""),
                                    "duration_min": t.get("duration_min", 30),
                                    "note":         t.get("note",""),
                                    "due_date":     None,
                                    "done":         False,
                                })
                            save_tasks(tasks_data)
                            st.success(f"✅ {len(new_tasks)}件のタスクを生成しました！")
                            st.rerun()

# ===== TAB2: 定期TASK =====
with tab2:
    st.markdown("### 毎週繰り返すタスクを登録")

    recurring = [t for t in tasks_data["tasks"] if t.get("type") == "recurring"]
    if recurring:
        for t in recurring:
            col = subj_color(t.get("subject",""))
            st.markdown(
                f'<div class="task-card" style="border-left-color:{col["primary"]};">'
                f'<div class="task-title">{col["emoji"]} {t["title"]}</div>'
                f'<div class="task-meta">毎週 {t.get("weekday","?")}曜　⏱ {t["duration_min"]}分　{t.get("subject","")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")
    with st.form("recurring_form"):
        st.markdown("**新しい定期タスクを追加**")
        r_subj = st.selectbox("教科", list(SUBJECT_COLOR.keys()), key="r_subj")
        r_title = st.text_input("タスク名", placeholder="例：漢字テスト対策")
        r_wd    = st.selectbox("曜日", ["月","火","水","木","金"])
        r_dur   = st.selectbox("時間", [15,20,30,45,60], index=2, format_func=lambda x: f"{x}分")
        if st.form_submit_button("追加", type="primary"):
            if r_title:
                import uuid
                tasks_data["tasks"].append({
                    "id":           str(uuid.uuid4())[:8],
                    "type":         "recurring",
                    "subject":      r_subj,
                    "title":        r_title,
                    "weekday":      r_wd,
                    "duration_min": r_dur,
                    "done":         False,
                })
                save_tasks(tasks_data)
                st.success("追加しました！")
                st.rerun()

# ===== TAB3: 自由TASK =====
with tab3:
    st.markdown("### 自由にタスクを追加")

    free_tasks = [t for t in tasks_data["tasks"] if t.get("type") == "free"]
    if free_tasks:
        for t in free_tasks:
            col = subj_color(t.get("subject",""))
            date_str = t.get("due_date","未割当")
            done_mark = "✅" if t.get("done") else "⬜"
            st.markdown(
                f'<div class="task-card" style="border-left-color:{col["primary"]};">'
                f'<div class="task-title">{done_mark} {t["title"]}</div>'
                f'<div class="task-meta">⏱ {t["duration_min"]}分　{t.get("subject","")}　'
                f'<span class="task-date">📅 {date_str}</span></div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")
    with st.form("free_form"):
        st.markdown("**新しいタスクを追加**")
        f_subj  = st.selectbox("教科", ["なし"] + list(SUBJECT_COLOR.keys()), key="f_subj")
        f_title = st.text_input("タスク名", placeholder="例：プリント整理")
        f_dur   = st.selectbox("時間", [15,20,30,45,60,90], index=2, format_func=lambda x: f"{x}分")
        f_note  = st.text_input("メモ", placeholder="任意")
        if st.form_submit_button("追加", type="primary"):
            if f_title:
                import uuid
                tasks_data["tasks"].append({
                    "id":           str(uuid.uuid4())[:8],
                    "type":         "free",
                    "subject":      f_subj if f_subj != "なし" else "",
                    "title":        f_title,
                    "duration_min": f_dur,
                    "note":         f_note,
                    "due_date":     None,
                    "done":         False,
                })
                save_tasks(tasks_data)
                st.success("追加しました！")
                st.rerun()

# ===== TAB4: スケジュール =====
with tab4:
    st.markdown("### タスクをカレンダーに配置")
    st.caption("日付を割り当てると TOP の Today's ToDo に表示されます")

    # 未割当タスク
    unscheduled = [t for t in tasks_data["tasks"] if not t.get("due_date") and not t.get("done")]
    scheduled   = [t for t in tasks_data["tasks"] if t.get("due_date")]

    if unscheduled:
        st.markdown("**📌 未割当のタスク**")
        for t in unscheduled:
            col = subj_color(t.get("subject",""))
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(
                    f'<div class="task-card" style="border-left-color:{col["primary"]};margin:4px 0;">'
                    f'<div class="task-title">{col["emoji"]} {t["title"]}</div>'
                    f'<div class="task-meta">⏱ {t["duration_min"]}分　{t.get("subject","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with c2:
                # 今日から14日分の日付を選択肢に
                date_options = {}
                for i in range(14):
                    d = today + timedelta(days=i)
                    wd = JP_WD[d.weekday()]
                    label = f"{d.month}/{d.day}（{wd}）"
                    date_options[label] = d.strftime("%Y-%m-%d")
                sel_label = st.selectbox(
                    "日付", list(date_options.keys()),
                    key=f"date_{t['id']}", label_visibility="collapsed"
                )
            with c3:
                if st.button("📅 配置", key=f"assign_{t['id']}", use_container_width=True):
                    for task in tasks_data["tasks"]:
                        if task["id"] == t["id"]:
                            task["due_date"] = date_options[sel_label]
                    save_tasks(tasks_data)
                    st.success("配置しました！")
                    st.rerun()

    st.markdown("---")
    st.markdown("**📅 配置済みタスク**")

    if scheduled:
        # 日付順にソート
        scheduled_sorted = sorted(scheduled, key=lambda x: x.get("due_date",""))
        cur_date = ""
        for t in scheduled_sorted:
            d = t.get("due_date","")
            if d != cur_date:
                cur_date = d
                try:
                    _d = datetime.strptime(d, "%Y-%m-%d")
                    wd = JP_WD[_d.weekday()]
                    st.markdown(f"**{_d.month}/{_d.day}（{wd}）**")
                except Exception:
                    st.markdown(f"**{d}**")
            col = subj_color(t.get("subject",""))
            done_mark = "✅" if t.get("done") else "⬜"
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(
                    f'<div class="task-card" style="border-left-color:{col["primary"]};margin:4px 0;">'
                    f'<div class="task-title">{done_mark} {col["emoji"]} {t["title"]}</div>'
                    f'<div class="task-meta">⏱ {t["duration_min"]}分</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with c2:
                done_btn = "✅" if not t.get("done") else "↩️"
                if st.button(done_btn, key=f"done_{t['id']}", use_container_width=True):
                    for task in tasks_data["tasks"]:
                        if task["id"] == t["id"]:
                            task["done"] = not task.get("done", False)
                    save_tasks(tasks_data)
                    st.rerun()
            with c3:
                if st.button("🗑️", key=f"del_{t['id']}", use_container_width=True):
                    tasks_data["tasks"] = [task for task in tasks_data["tasks"]
                                          if task["id"] != t["id"]]
                    save_tasks(tasks_data)
                    st.rerun()
    else:
        st.caption("まだタスクが配置されていません")
