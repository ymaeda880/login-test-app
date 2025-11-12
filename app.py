# login_test_app/app.py
from __future__ import annotations
from pathlib import Path
import sys
import os
import time
import datetime as dt
from typing import Any, Dict, List, Optional

import streamlit as st
import extra_streamlit_components as stx
import jwt  # 署名未検証で payload を覗くデバッグ用（本番の検証は verify_jwt）

# ─────────────────────────────────────────────────────────────
# 0) import path bootstrap（common_lib を探す / projects ルートを特定）
# ─────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve()

def _find_projects_root(start: Path) -> Optional[Path]:
    # 祖先に 'projects' というディレクトリ名があればそれを返す
    for p in [start, *start.parents]:
        if p.name == "projects":
            return p
    # 祖先の直下に projects/ がある場合も拾う
    for p in [start, *start.parents]:
        candidate = p / "projects"
        if candidate.is_dir():
            return candidate
    return None

PROJECTS_ROOT = _find_projects_root(HERE)
if PROJECTS_ROOT and str(PROJECTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECTS_ROOT))

def _add_commonlib_parent_to_syspath() -> Optional[str]:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "common_lib").is_dir():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return str(parent)
    # projects 直下の common_lib も試す
    if PROJECTS_ROOT and (PROJECTS_ROOT / "common_lib").is_dir():
        if str(PROJECTS_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECTS_ROOT))
        return str(PROJECTS_ROOT)
    return None

_add_commonlib_parent_to_syspath()

# ─────────────────────────────────────────────────────────────
# 1) 共通ライブラリ（JWT検証・UI）
# ─────────────────────────────────────────────────────────────
from common_lib.ui.ui_basics import thick_divider
from common_lib.auth.jwt_utils import verify_jwt  # JWTはユーザー名のみ想定
from common_lib.auth.config import COOKIE_NAME, PORTAL_URL

# ─────────────────────────────────────────────────────────────
# 2) settings.toml ローダ（lib.access_settings が無くても動くフォールバック）
# ─────────────────────────────────────────────────────────────
def load_access_settings() -> Dict[str, Any]:
    """
    auth_portal_app/.streamlit/settings.toml を読み込んで dict を返す。
    環境変数 → 典型パス → 自動探索 の順に検索。
    """
    # 2.1 明示指定（最優先）
    env_path = os.environ.get("AUTH_PORTAL_SETTINGS_FILE") or os.environ.get("ADMIN_SETTINGS_FILE")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.is_file():
            return _read_toml(p)

    # 2.2 典型パス（projects 直下の auth_portal_project/auth_portal_app）
    if PROJECTS_ROOT:
        classic = PROJECTS_ROOT / "auth_portal_project" / "auth_portal_app" / ".streamlit" / "settings.toml"
        if classic.is_file():
            return _read_toml(classic)

    # 2.3 自動探索（auth_portal_app/.streamlit/settings.toml を深さ制限付きで探索）
    search_roots: List[Path] = []
    if PROJECTS_ROOT:
        search_roots.append(PROJECTS_ROOT)
    # 祖先の下層も少し見る（大規模リポで projects が別名の時の保険）
    search_roots.extend([p for p in HERE.parents[:3]])

    visited = set()
    for root in search_roots:
        root = root.resolve()
        if not root.exists() or root in visited:
            continue
        visited.add(root)
        # 深さ優先で最大深さ 4 くらいに制限
        for sub in _iter_dirs_bounded(root, max_depth=4):
            candidate = sub / "auth_portal_app" / ".streamlit" / "settings.toml"
            if candidate.is_file():
                return _read_toml(candidate)

    # 2.4 最後の保険：カレントから上に遡って .streamlit/settings.toml を拾う
    for p in [HERE.parent, *HERE.parents]:
        candidate = p / ".streamlit" / "settings.toml"
        if candidate.is_file():
            return _read_toml(candidate)

    st.error("settings.toml が見つかりませんでした。AUTH_PORTAL_SETTINGS_FILE を環境変数で指定するか、"
             "auth_portal_app/.streamlit/settings.toml を配置してください。")
    return {}

def _iter_dirs_bounded(root: Path, max_depth: int = 3):
    """ルート以下のディレクトリを深さ制限付きで列挙（ファイル数が多い環境の暴走防止）。"""
    from collections import deque
    dq = deque([(root, 0)])
    while dq:
        base, d = dq.popleft()
        if d > max_depth:
            continue
        yield base
        try:
            for child in base.iterdir():
                if child.is_dir():
                    dq.append((child, d + 1))
        except Exception:
            continue

def _read_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # Py3.11+
        with path.open("rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        st.error(f"TOML 読み込みに失敗しました: {path}\n{e}")
        return {}

# ─────────────────────────────────────────────────────────────
# 3) 基本メタ情報（APP_BASE → APP_KEY）
# ─────────────────────────────────────────────────────────────
APP_BASE = "/login_test"
APP_KEY  = APP_BASE.strip("/").split("/")[-1] or "login_test"

# ─────────────────────────────────────────────────────────────
# 4) Streamlit ページ設定
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Login Test App", page_icon="🧪", layout="wide")
st.title("🧪 Login Test App（JWT: ユーザー名のみ｜ACLは settings.toml を直接参照）")

# ─────────────────────────────────────────────────────────────
# 5) ユーティリティ
# ─────────────────────────────────────────────────────────────
def _portal_url_with_next(next_path: str) -> str:
    next_norm = next_path.rstrip("/") + "/"
    return f"{PORTAL_URL}?next={next_norm}"

def portal_button(label: str = "🔐 ポータルを開く / 再ログイン"):
    target = _portal_url_with_next(APP_BASE)
    if st.button(label, use_container_width=False):
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={target}"/>',
            unsafe_allow_html=True,
        )

def decode_without_verify(token: str | None) -> Dict[str, Any]:
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

# ─────────────────────────────────────────────────────────────
# 6) 上部/サイドバー ナビ
# ─────────────────────────────────────────────────────────────
top_cols = st.columns([1, 1, 6])
with top_cols[0]:
    if st.button("🔐 ポータルへ戻る", key="btn_to_portal_top"):
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={_portal_url_with_next(APP_BASE)}"/>',
            unsafe_allow_html=True,
        )

st.sidebar.markdown("### ナビゲーション")
if st.sidebar.button("🔐 ポータルへ戻る", key="btn_to_portal_sidebar"):
    st.sidebar.markdown(
        f'<meta http-equiv="refresh" content="0; url={_portal_url_with_next(APP_BASE)}"/>',
        unsafe_allow_html=True,
    )

thick_divider()

# ─────────────────────────────────────────────────────────────
# 7) 認証チェック（自動リダイレクトなし・診断表示）
# ─────────────────────────────────────────────────────────────
cm = stx.CookieManager()
raw_token = cm.get(COOKIE_NAME)

if not raw_token:
    st.warning("Cookie が見つかりません（未ログインの可能性）。この場では自動遷移しません。")
    with st.expander("🔎 デバッグ：Cookie 状況", expanded=True):
        st.write({"cookie_present": False, "cookie_name": COOKIE_NAME})
        st.info("対処：下のボタンからポータルを開いてログインしてください。")
    portal_button()
    st.stop()

payload = verify_jwt(raw_token)  # sub のみ想定
if not payload:
    weak = decode_without_verify(raw_token)
    exp  = weak.get("exp")
    now  = int(time.time())
    reason = "トークンが無効です（署名不一致・破損等の可能性）。"
    if isinstance(exp, int) and exp < now:
        reason = "トークンの有効期限が切れています。"

    st.error(f"{reason}（このページは自動遷移しません）")
    with st.expander("🔎 デバッグ：JWT の推定内容（署名未検証）", expanded=True):
        st.write({
            "decoded_without_verify": weak,
            "exp_human": human_time(exp),
            "now_human": human_time(now),
            "seconds_until_expire": (exp - now) if isinstance(exp, int) else None,
        })
        st.caption("※ 上記は署名検証なしの参考情報です。")
    portal_button("🔐 ポータルで再ログイン")
    st.stop()

current_user: str = (payload.get("sub") or "unknown")

# ─────────────────────────────────────────────────────────────
# 8) ACL 読み込み & 権限チェック（settings.toml 直接参照）
# ─────────────────────────────────────────────────────────────
ACL = load_access_settings()

ACCESS = ACL.get("access", {}) if isinstance(ACL, dict) else {}
PUBLIC = (ACCESS.get("public", {}) or {}).get("apps", []) or []
USER   = (ACCESS.get("user", {}) or {}).get("apps", []) or []
RESTR  = (ACCESS.get("restricted", {}) or {}).get("apps", []) or []
ADMIN  = (ACCESS.get("admin", {}) or {}).get("apps", []) or []
RU     = ACL.get("restricted_users", {}) if isinstance(ACL, dict) else {}

_raw_admin = ACL.get("admin_users", []) if isinstance(ACL, dict) else []
if isinstance(_raw_admin, dict):
    ADMINS = set(_raw_admin.get("users", []))
elif isinstance(_raw_admin, (list, tuple, set)):
    ADMINS = set(_raw_admin)
else:
    ADMINS = set()

allowed = False
reason  = ""

if APP_KEY in PUBLIC:
    allowed = True
    reason  = "public"
elif current_user in ADMINS:
    allowed = True
    reason  = "admin_user"
elif APP_KEY in USER:
    allowed = True
    reason  = "user_layer"
elif APP_KEY in RESTR:
    allowed = current_user in (RU.get(APP_KEY, []) or [])
    reason  = "restricted_users"
else:
    allowed = False
    reason  = "unlisted_app"

if not allowed:
    st.error(f"このユーザーには **{APP_KEY}** の権限がありません。")
    with st.expander("🔎 デバッグ：ACL 状況", expanded=True):
        st.write({
            "APP_KEY": APP_KEY,
            "current_user": current_user,
            "reason": reason,
            "public_apps": sorted(set(PUBLIC)),
            "user_apps": sorted(set(USER)),
            "restricted_apps": sorted(set(RESTR)),
            "admin_apps": sorted(set(ADMIN)),
            "restricted_users_for_app": RU.get(APP_KEY, []),
            "admin_users": sorted(ADMINS),
            "PROJECTS_ROOT": str(PROJECTS_ROOT) if PROJECTS_ROOT else None,
        })
        st.caption("※ 判定は settings.toml を直接参照しています。")
    portal_button("🔐 ポータル（管理者に権限付与を依頼）")
    st.stop()

# ─────────────────────────────────────────────────────────────
# 9) 本体
# ─────────────────────────────────────────────────────────────
st.success(f"✅ ログインしました — ユーザー: **{current_user}**")
with st.expander("🔎 参考：JWT payload（検証済み。appsは含めません）", expanded=False):
    st.write(payload)

thick_divider()

st.subheader("ページ案内")
st.markdown("- **保護テスト**（ログイン必須） → サイドバーの pages から開けます")
st.markdown("- **公開テスト**（ログイン不要） → サイドバーの pages から開けます")

thick_divider()

# ─────────────────────────────────────────────────────────────
# 10) ログアウト
# ─────────────────────────────────────────────────────────────
st.subheader("ログアウト")
if st.button("ログアウト", key="btn_logout_root", use_container_width=True):
    try:
        cm.delete(COOKIE_NAME, path="/")
    except TypeError:
        cm.delete(COOKIE_NAME)
    st.success("ログアウトしました。（このページは自動リダイレクトしません）")
    st.info("必要なら下のボタンからポータルへ。")
    portal_button("🔐 ポータルへ")
