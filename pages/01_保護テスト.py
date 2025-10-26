# login_test_app/pages/01_保護テスト.py
from __future__ import annotations
from pathlib import Path
import sys
import json, time
import datetime as dt
import streamlit as st
import extra_streamlit_components as stx
import jwt  # デバッグ用：署名検証なしで中身確認に使う

# ========= projects/ を import ルートに追加（pages配下なので parents[3]）=========
PROJECTS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECTS_ROOT))

# 共通UI & JWTユーティリティ
from common_lib.ui.ui_basics import thick_divider
from common_lib.auth.jwt_utils import verify_jwt  # 有効: dict / 無効: None

# ===== 設定 =====
LOGIN_URL = "/auth_portal"        # ポータル
APP_BASE  = "/login_test"         # このアプリの公開パス
APP_NAME_FOR_ACL = (APP_BASE.strip("/").split("/")[-1] or "login_test")
REQUIRE_ACL = False               # ← 必要なら True（JWT payload['apps'] に APP_NAME_FOR_ACL が必要）

st.set_page_config(page_title="保護テスト", page_icon="🔒")
st.title("🔒 保護テスト（JWT Cookie 方式｜その場で診断・非リダイレクト）")

# ===== 共有データ保存先（相対で安定）=====
HERE = Path(__file__).resolve()
app_dir = HERE.parent if HERE.parent.name != "pages" else HERE.parent.parent   # .../login_test_app
project_dir = app_dir.parent                                                    # .../login_test_project
DATA_DIR = project_dir / "data"                                                # プロジェクト直下 data/
LOG_DIR  = DATA_DIR / "events"
LOG_FILE = LOG_DIR / "button_clicks.jsonl"     # 1行1イベント(JSON)

# ===== ユーティリティ =====
def portal_button(label: str = "🔐 ポータルを開く"):
    next_url = APP_BASE.rstrip("/") + "/"  # /login_test/
    if st.button(label, use_container_width=False):
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={LOGIN_URL}?next={next_url}"/>',
            unsafe_allow_html=True
        )

def decode_without_verify(token: str | None) -> dict:
    """署名検証なしでデコード（デバッグ用）。"""
    if not token:
        return {}
    try:
        return jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception:
        return {}

def human_time(epoch: int | float | None) -> str:
    if not epoch:
        return "-"
    try:
        return dt.datetime.fromtimestamp(int(epoch)).isoformat(sep=" ", timespec="seconds")
    except Exception:
        return str(epoch)

# ---- クリック記録ヘルパ
def append_click_event(user: str, button_id: str, meta: dict | None = None) -> None:
    """
    JSONL に追記: 1行 = 1イベント
    {ts, iso, month, app, page, user, button, meta}
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = int(time.time())
    d = dt.datetime.fromtimestamp(now)
    event = {
        "ts": now,
        "iso": d.isoformat(timespec="seconds"),
        "month": d.strftime("%Y-%m"),
        "app": APP_NAME_FOR_ACL,
        "page": "01_保護テスト",
        "user": user,
        "button": button_id,
        "meta": meta or {},
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def load_events(max_lines: int | None = None) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if max_lines and max_lines > 0:
        rows = rows[-max_lines:]
    return rows

def aggregate_by_user_month(rows: list[dict]) -> list[dict]:
    """ユーザー×月×ボタンの件数を集計"""
    from collections import defaultdict
    agg = defaultdict(int)
    for r in rows:
        user = r.get("user") or "unknown"
        month = r.get("month") or "unknown"
        btn = r.get("button") or "-"
        agg[(user, month, btn)] += 1
    out = []
    for (user, month, btn), cnt in sorted(agg.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
        out.append({"user": user, "month": month, "button": btn, "count": cnt})
    return out

# ===== 認証（CookieのJWTのみ使用）=====
cm = stx.CookieManager()
raw_token = cm.get("prec_sso")
payload   = verify_jwt(raw_token) if raw_token else None

if not raw_token:
    st.warning("Cookie（prec_sso）がありません。未ログインの可能性があります。")
    with st.expander("🔎 デバッグ：Cookie状態", expanded=True):
        st.write({"cookie_present": False})
        st.info("対処: 下のボタンでポータルを開き、ログインしてください。")
    portal_button()
    st.stop()

if not payload:
    weak = decode_without_verify(raw_token)
    now  = int(time.time())
    exp  = weak.get("exp")
    reason = "トークンが無効です（署名不一致、壊れている、または発行者/受信者の不一致）。"
    if isinstance(exp, int) and exp < now:
        reason = "トークンの有効期限が切れています。"
    st.error(f"{reason}（自動遷移しません）")
    with st.expander("🔎 デバッグ：JWT推定内容（署名未検証）", expanded=True):
        st.write({
            "decoded_without_verify": weak,
            "exp_human": human_time(exp),
            "now_human": human_time(now),
            "seconds_until_expire": (exp - now) if isinstance(exp, int) else None,
        })
    portal_button("🔐 ポータルで再ログイン")
    st.stop()

# ここまで来れば有効なJWT
current_user = payload.get("sub", "") or "unknown"
apps = payload.get("apps", []) or []

st.success(f"✅ ログインOK: **{current_user}**")
st.caption(f"権限（apps）: {sorted(apps)}")

# ===== 任意 ACL チェック（JWTのappsのみを見る）=====
if REQUIRE_ACL:
    if APP_NAME_FOR_ACL not in apps:
        st.error(f"このアプリ **{APP_NAME_FOR_ACL}** を利用する権限がありません。")
        with st.expander("🔎 デバッグ：ACL", expanded=True):
            st.write({"APP_NAME_FOR_ACL": APP_NAME_FOR_ACL, "jwt.apps": apps})
        portal_button("🔐 ポータル（管理者に権限付与を依頼）")
        st.stop()

# ===== 本文 =====
st.info("ここは『ログイン必須』ページです。JWT Cookie（prec_sso）で認証しています。")

with st.expander("🔎 JWT payload（検証済み）", expanded=False):
    st.write(payload)

thick_divider()
st.subheader("操作（押下記録つき）")

# --- 記録対象ボタン（例として3種類）
bcols = st.columns(3)
with bcols[0]:
    if st.button("👍 いいね", key="btn_like", use_container_width=True):
        append_click_event(current_user, "like")
        st.success("記録しました（いいね）")
with bcols[1]:
    if st.button("✅ 完了", key="btn_done", use_container_width=True):
        append_click_event(current_user, "done")
        st.success("記録しました（完了）")
with bcols[2]:
    if st.button("⭐ ブックマーク", key="btn_star", use_container_width=True):
        append_click_event(current_user, "star")
        st.success("記録しました（ブックマーク）")

st.caption("※ クリックは data/events/button_clicks.jsonl に追記されます。")

thick_divider()
st.subheader("ユースケース別操作")
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 トークン再確認（画面更新）"):
        st.rerun()
with col2:
    if st.button("🚪 ログアウト（Cookie削除）", use_container_width=True):
        try:
            # CookieManager.delete() は実装によって path 引数を受け取らないことがある
            cm.delete("prec_sso")
        except TypeError:
            # fallback: 空Cookieで上書き＆期限切れに
            cm.set("prec_sso", "", expires_at=dt.datetime.utcnow() - dt.timedelta(days=1))

        st.success("ログアウトしました。（リダイレクトはしません）")
        st.info("必要なら下のボタンからポータルへ。")
        portal_button("🔐 ポータルへ")

# ===== 簡易集計ビュー =====
thick_divider()
st.subheader("📈 簡易集計（ユーザー×月×ボタン）")
rows = load_events()
if not rows:
    st.caption("まだ記録がありません。上のボタンを押してみてください。")
else:
    with st.expander("🧾 直近の記録（末尾20件）", expanded=False):
        tail = rows[-20:] if len(rows) > 20 else rows
        st.json(tail)

    agg = aggregate_by_user_month(rows)
    st.table(agg)
