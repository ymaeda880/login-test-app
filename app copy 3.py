# login_test_app/app.py
from __future__ import annotations
from pathlib import Path
import sys
import time
import datetime as dt

import streamlit as st
import extra_streamlit_components as stx
import jwt  # デバッグ用（署名未検証で中身を覗く）

# ========= projects/ を import ルートに追加 =========
PROJECTS_ROOT = Path(__file__).resolve().parents[2]  # pages/*.py なら 3 に変更
if str(PROJECTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECTS_ROOT))

# ========= common_lib から共通UIとJWTユーティリティ =========
from common_lib.ui.ui_basics import thick_divider
from common_lib.auth.jwt_utils import issue_jwt, verify_jwt  # 検証で使用（発行はデバッグ用）
from common_lib.auth.config import COOKIE_NAME, PORTAL_URL

# ================= 基本設定 =================

APP_BASE    = "/login_test"
APP_KEY     = APP_BASE.strip("/").split("/")[-1] or "login_test"

st.set_page_config(page_title="Login Test App", page_icon="🧪", layout="wide")
st.title("🧪 Login Test App（JWT Cookie 方式｜その場で診断・非リダイレクト）")

# === 上部のナビボタン ===
top_cols = st.columns([1, 1, 6])
with top_cols[0]:
    if st.button("🔐 ポータルへ戻る", key="btn_to_portal_top"):
        next_url = APP_BASE.rstrip("/") + "/"
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={PORTAL_URL}?next={next_url}"/>',
            unsafe_allow_html=True,
        )

# === サイドバーのナビボタン ===
st.sidebar.markdown("### ナビゲーション")
if st.sidebar.button("🔐 ポータルへ戻る", key="btn_to_portal_sidebar"):
    next_url = APP_BASE.rstrip("/") + "/"
    st.sidebar.markdown(
        f'<meta http-equiv="refresh" content="0; url={PORTAL_URL}?next={next_url}"/>',
        unsafe_allow_html=True,
    )

thick_divider()

# ================= ユーティリティ =================
def portal_button(label: str = "🔐 ポータルを開く"):
    """ポータルへ送ってログイン（または再ログイン）させるショートカット"""
    next_url = APP_BASE.rstrip("/") + "/"  # /login_test/
    if st.button(label, use_container_width=False):
        st.markdown(f'<meta http-equiv="refresh" content="0; url={PORTAL_URL}?next={next_url}"/>',
                    unsafe_allow_html=True)

def decode_without_verify(token: str | None) -> dict:
    """署名検証なしで中身だけ覗く（デバッグ用）。tokenが無ければ空。"""
    if not token:
        return {}
    try:
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}

def human_time(epoch: int | float | None) -> str:
    if not epoch:
        return "-"
    try:
        return dt.datetime.fromtimestamp(int(epoch)).isoformat(sep=" ", timespec="seconds")
    except Exception:
        return str(epoch)

# ================= 認証チェック（非リダイレクト） =================
cm = stx.CookieManager()
raw_token = cm.get(COOKIE_NAME)

if not raw_token:
    st.warning("Cookie が見つかりません（未ログインの可能性）。この場ではリダイレクトしません。")
    with st.expander("🔎 デバッグ：Cookie状況", expanded=True):
        st.write({"cookie_present": False})
        st.info("対処: 下のボタンでポータルを開いてログインしてください。")
    portal_button()
    st.stop()

# JWT 検証（PyJWT）
payload = verify_jwt(raw_token)

if not payload:
    # 期限切れ等の判別用に署名検証なしで中身を確認
    weak = decode_without_verify(raw_token)
    exp  = weak.get("exp")
    now  = int(time.time())
    reason = "トークンが無効です（署名不一致か破損の可能性）。"
    if isinstance(exp, int) and exp < now:
        reason = "トークンの有効期限が切れています。"

    st.error(f"{reason}（自動遷移は行いません）")
    with st.expander("🔎 デバッグ：JWTの推定内容（署名未検証）", expanded=True):
        st.write({
            "decoded_without_verify": weak,
            "exp_human": human_time(exp),
            "now_human": human_time(now),
            "seconds_until_expire": (exp - now) if isinstance(exp, int) else None,
        })
        st.caption("※ 上記は署名検証なしの参考情報です。")
    portal_button("🔐 ポータルで再ログイン")
    st.stop()

# ここまで来れば有効
current_user = payload.get("sub", "") or "unknown"
st.success(f"✅ ログインしました — ユーザー: **{current_user}**")

# ================= 権限チェック（非リダイレクト） =================
apps = payload.get("apps", []) or []
if APP_KEY not in apps:
    st.error(f"このユーザーには **{APP_KEY}** の権限がありません。")
    with st.expander("🔎 デバッグ：ACL", expanded=True):
        st.write({"APP_KEY": APP_KEY, "jwt.apps": apps})
    portal_button("🔐 ポータル（管理者に権限付与を依頼）")
    st.stop()

# ================= ページ本体 =================
with st.expander("🔎 JWT payload（検証済み）", expanded=False):
    st.write(payload)
st.caption(f"権限（apps）: {sorted(apps)}")

thick_divider()

st.subheader("ページ案内")
st.markdown("- **保護テスト**（ログイン必須） → サイドバーの pages から開けます")
st.markdown("- **公開テスト**（ログイン不要） → サイドバーの pages から開けます")

# ================= ログアウト =================
thick_divider()
st.subheader("ログアウト")
if st.button("ログアウト", key="btn_logout_root", use_container_width=True):
    try:
        cm.delete(COOKIE_NAME, path="/")
    except TypeError:
        # 古いバージョンのESCで path 指定が不要/未対応な場合もある
        cm.delete(COOKIE_NAME)
    st.success("ログアウトしました。（このページはリダイレクトしません）")
    st.info("必要なら下のボタンからポータルへ。")
    portal_button("🔐 ポータルへ")

# （任意）デバッグ: 手元で再発行して動作確認したい場合は下記を一時的に使う
# with st.expander("🛠 開発者向け：ローカルでテストトークン発行（本番では使わない）", expanded=False):
#     if st.button("テストトークンを上書き発行"):
#         # ※ 実運用は auth_portal 側で発行する。ここは開発検証用オプション。
#         fake_apps = sorted(set(apps + [APP_KEY]))
#         token, _exp = issue_jwt(current_user or "tester", apps=fake_apps)
#         cm.set(COOKIE_NAME, token, max_age=8*3600, path="/", same_site="Lax")
#         st.success("テストトークンを上書きしました。手動でリロードしてください。")
