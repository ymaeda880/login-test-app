# login_test_app/app.py
from __future__ import annotations
import json
from pathlib import Path
import streamlit as st

# ===== 共有データの場所を「相対で」特定（pages/からの実行にも対応）=====
HERE = Path(__file__).resolve()
app_dir = HERE.parent if HERE.parent.name != "pages" else HERE.parent.parent  # .../login_test_app
project_dir  = app_dir.parent              # .../login_test_project
projects_dir = project_dir.parent          # .../projects
DATA_DIR = projects_dir / "auth_portal_project" / "auth_portal_app" / "data"

USERS_FILE       = DATA_DIR / "users.json"        # {"users": {"name": {"pw":"...", "apps":[...]}}}
LOGIN_USERS_FILE = DATA_DIR / "login_users.json"  # {"user": {"login_time" or last_login/last_seen など任意, "apps":[...]}}
PORTAL_URL = "/auth_portal"
APP_BASE   = "/login_test"                        # このアプリの公開パス
APP_KEY    = APP_BASE.strip("/").split("/")[-1] or "login_test"

st.set_page_config(page_title="Login Test App", page_icon="🧪", layout="wide")
st.title("🧪 Login Test App（login_users.json 方式｜相対解決・表記ゆれ吸収なし）")

# ---------- ユーティリティ ----------
def load_json(p: Path, default):
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return default

def save_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- データ読込（そのまま。表記ゆれの正規化は一切しない）----------
users_db       = load_json(USERS_FILE, {"users": {}}).get("users", {})
login_users    = load_json(LOGIN_USERS_FILE, {})   # キーや値はそのまま使う

# ---------- クエリ ?user=xxx をまず表示 ----------
# qp = dict(st.query_params)
# q_user = qp.get("user")
# if isinstance(q_user, list):
#     q_user = q_user[0] if q_user else None

# with st.expander("🔎 Debug — Query", expanded=True):
#     st.write({
#         "raw_query_params": qp,
#         "q_user": q_user,
#     })

# # 表示後に、q_user があればセッションへ保存して URL をクリーン化
# if q_user:
#     st.session_state["current_user"] = q_user
#     # クリーンURLへ（?user を消す）
#     st.markdown('<meta http-equiv="refresh" content="0; url=./"/>', unsafe_allow_html=True)
#     st.stop()

###############


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


################

# ---------- 現在ユーザーの決定 ----------
cur = st.session_state.get("current_user")

# cur が未設定：login_users に1人だけ居るなら自動確定
if not cur and len(login_users) == 1:
    cur = next(iter(login_users.keys()))
    st.session_state["current_user"] = cur

# cur があるのに login_users にいない場合でも、users.json に登録があれば有効とみなす
if cur and (cur not in login_users) and (cur in users_db):
    pass  # そのまま通す

# まだ未確定なら選択UI
if not st.session_state.get("current_user"):
    st.warning("ログイン中のユーザーが特定できません。ユーザーを選択してください。")
    if not login_users:
        st.info("login_users.json にログイン中ユーザーがいません。ポータルでログインしてください。")
        st.markdown(f'[➡ ポータルへ]({PORTAL_URL}/)')
        with st.expander("🔎 Debug — Paths"):
            st.write({
                "DATA_DIR": str(DATA_DIR),
                "LOGIN_USERS_FILE": str(LOGIN_USERS_FILE),
                "USERS_FILE": str(USERS_FILE),
            })
        st.stop()

    pick = st.selectbox("ログイン中のユーザー", options=list(login_users.keys()), index=0)
    if st.button("このユーザーで続行", use_container_width=True):
        st.session_state["current_user"] = pick
        st.rerun()
    st.stop()

# ここまで来れば確定
cur = st.session_state.get("current_user")
st.success(f"ログイン中: **{cur}**")

# ---------- ACL: users.json を優先、無ければ login_users.json.apps ----------
def allowed_apps(user: str) -> set[str]:
    rec = users_db.get(user, {})
    apps = rec.get("apps")
    if not apps:
        # login_users の値はそのまま使う（apps が無ければ空扱い）
        apps = (login_users.get(user, {}) or {}).get("apps", [])
    return set(apps or [])

allow = allowed_apps(cur)
if APP_KEY not in allow:
    st.error(f"このユーザーには **{APP_KEY}** の権限がありません。")
    st.markdown(f'[➡ ポータルへ戻る]({PORTAL_URL}/)')
    with st.expander("🔎 Debug — ACL"):
        st.write({"APP_KEY": APP_KEY, "allowed_apps": sorted(list(allow))})
    st.stop()

st.caption(f"権限: {sorted(list(allow))}")

# ---------- ページ案内 ----------
st.divider()
st.subheader("ページ")
st.markdown("- **保護テスト**（ログイン必須） → サイドバーの pages から開けます")
st.markdown("- **公開テスト**（ログイン不要） → サイドバーの pages から開けます")

# ---------- ログアウト：login_users.json から当該ユーザーを除去 ----------
st.divider()
st.subheader("ログアウト（login_users.json から除去）")
if st.button("ログアウト", key="btn_logout_root"):
    data = load_json(LOGIN_USERS_FILE, {})
    if cur in data:
        del data[cur]
        save_json(LOGIN_USERS_FILE, data)
    st.session_state.pop("current_user", None)
    st.success("ログアウトしました。")
    st.markdown(f'<meta http-equiv="refresh" content="0; url={PORTAL_URL}/"/>', unsafe_allow_html=True)

# ---------- デバッグ ----------
with st.expander("🔎 Debug — ファイル/状態"):
    st.write({
        "DATA_DIR": str(DATA_DIR),
        "USERS_FILE": str(USERS_FILE),
        "LOGIN_USERS_FILE": str(LOGIN_USERS_FILE),
        "login_users_keys": list(login_users.keys()),
        "current_user": st.session_state.get("current_user"),
        "users_db_has_current": cur in users_db if cur else None,
        "login_users_has_current": cur in login_users if cur else None,
    })
