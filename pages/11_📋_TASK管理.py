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
NEXT_TEST = {
    "name": "1学期 期末テスト",
    "start_date": "2026-06-18",
    "subjects": [
        {"subject": "技術家庭", "date": "6/18(木)", "range": "教科書 P30-55",                        "study_hours": 2},
        {"subject": "国語",     "date": "6/18(木)", "range": "漢字+文法+読解「故郷」/📝ワーク提出",  "study_hours": 5},
        {"subject": "社会",     "date": "6/18(木)", "range": "歴史 P105-160",                        "study_hours": 8},
        {"subject": "保健体育", "date": "6/18(木)", "range": "教科書 P20-40",                        "study_hours": 2},
        {"subject": "数学",     "date": "6/19(金)", "range": "1年範囲+文章題+連立方程式",            "study_hours": 12},
        {"subject": "英語",     "date": "6/19(金)", "range": "Unit 1-3+英作文",                      "study_hours": 3},
        {"subject": "理科",     "date": "6/19(金)", "range": "化学変化+生物",                        "study_hours": 4},
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
def generate_tasks_ai(subject, test_range, study_hours, test_date_str):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY",""))
        prompt = (
            f"中学2年生の{subject}の期末テスト対策タスクを生成してください。\n\n"
            f"テスト日: {test_date_str}\n"
            f"テスト範囲: {test_range}\n"
            f"合計勉強時間の目安: {study_hours}時間\n\n"
            f"【ルール】\n"
            f"- タスクを3〜5個に分割する\n"
            f"- 各タスクは具体的な内容（例：「P105-120を読む」「ワークP.2-5を解く」）\n"
            f"- duration_minは15〜60の整数（分）\n"
            f"- 合計時間が study_hours×60分 に近くなるようにする\n"
            f"- JSONのみ出力\n\n"
            f"出力フォーマット:\n"
            f'[{{"title":"タスク名","duration_min":30,"note":"補足"}},...]'
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            response_format={"type": "json_object"},
            messages=[
                {"role":"system","content":"タスクリストをJSONで返してください。キー名は'tasks'で配列を返してください。"},
                {"role":"user","content":prompt}
            ]
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("tasks", data) if isinstance(data, dict) else data
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
        range_ = subj_info["range"]
        hours  = subj_info["study_hours"]

        with st.expander(f"{col['emoji']} {subj}　範囲: {range_}　目安: {hours}h", expanded=False):
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
                        new_tasks = generate_tasks_ai(subj, range_, hours, NEXT_TEST["start_date"])
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
