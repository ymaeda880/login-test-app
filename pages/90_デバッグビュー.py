# login_test_app/pages/90_デバッグビュー.py
from __future__ import annotations
import json
from pathlib import Path
import datetime as dt
import streamlit as st

# ========= パス解決（pages配下から実行しても壊れない相対解決）=========
HERE = Path(__file__).resolve()
app_dir = HERE.parent if HERE.parent.name != "pages" else HERE.parent.parent      # .../login_test_app
project_dir  = app_dir.parent                                                     # .../login_test_project
projects_dir = project_dir.parent                                                 # .../projects

DATA_DIR = projects_dir / "auth_portal_project" / "auth_portal_app" / "data"
USERS_FILE = DATA_DIR / "users.json"
LOGIN_USERS_FILE = DATA_DIR / "login_users.json"

st.set_page_config(page_title="デバッグビュー", page_icon="🔎", layout="wide")
st.title("🔎 デバッグビュー（login_users.json / users.json / URLクエリ）")

# ========= ユーティリティ =========
def load_json(p: Path, default):
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return default

def stat_info(p: Path):
    if not p.exists():
        return {"exists": False}
    s = p.stat()
    return {
        "exists": True,
        "size_bytes": s.st_size,
        "mtime_iso": dt.datetime.fromtimestamp(s.st_mtime).isoformat(timespec="seconds"),
        "path": str(p),
    }

# ========= URLクエリ =========
qp = dict(st.query_params)
q_user = qp.get("user")
if isinstance(q_user, list):
    q_user = q_user[0] if q_user else None

# Debug: q_user の値を確認
st.write("➡ q_user =", q_user)

if q_user:
    st.session_state["current_user"] = q_user   # ← ここで入れている！
    # st.rerun()                     # ← これでセッションを保持して再実行



# Debug: t.session_state['current_user']の値を確認
st.write("➡ st.session_state['current_user'] =", st.session_state.get("current_user"))


with st.expander("🧭 URLクエリ", expanded=True):
    st.write({"raw_query_params": qp, "q_user": q_user})


# ========= セッション状態 =========
with st.expander("🧠 Session State", expanded=True):
    st.write({
        "session_current_user": st.session_state.get("current_user"),
        "all_session_keys": list(st.session_state.keys()),
    })

# ========= ファイルの場所・状態 =========
st.subheader("📁 ファイルの場所・状態")
cols = st.columns(2)
with cols[0]:
    st.caption("users.json（登録ユーザー & 権限）")
    st.json(stat_info(USERS_FILE))
with cols[1]:
    st.caption("login_users.json（現在ログイン中ユーザー）")
    st.json(stat_info(LOGIN_USERS_FILE))

# ========= 中身を表示 =========
st.subheader("📘 users.json の中身")
users_root = load_json(USERS_FILE, {"users": {}})
st.json(users_root)

st.subheader("👥 login_users.json の中身")
login_users = load_json(LOGIN_USERS_FILE, {})
st.json(login_users)

# ========= 派生ビュー（見やすさ用）=========
st.subheader("🧩 まとめビュー")
users_db = users_root.get("users", {}) if isinstance(users_root, dict) else {}
usernames_users_json = sorted(list(users_db.keys()))
usernames_login_users = sorted(list(login_users.keys()))

st.write({
    "users.json に居るユーザー": usernames_users_json,
    "login_users.json に居るユーザー": usernames_login_users,
})

# 指定ユーザーの権限などを軽く確認（q_user または session の current_user）
focus_user = q_user or st.session_state.get("current_user")
st.caption("フォーカスするユーザー（q_user → session の順で採用）")
st.code(focus_user or "(なし)")

if focus_user:
    u_apps = (users_db.get(focus_user, {}) or {}).get("apps", [])
    l_apps = (login_users.get(focus_user, {}) or {}).get("apps", [])
    st.write({
        "users.json 側 apps": u_apps,
        "login_users.json 側 apps": l_apps,
    })

st.divider()
st.caption(f"DATA_DIR: {DATA_DIR}")
