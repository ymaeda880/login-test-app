# login_test_app/pages/10_クッキー最小テスト.py
from __future__ import annotations
import time
import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(page_title="Cookie 最小テスト（安定版）", page_icon="🍪", layout="centered")
st.title("🍪 Cookie 最小テスト（rerun安定版）")

# 何回目の実行か可視化（デバッグ用）
st.session_state["run_count"] = st.session_state.get("run_count", 0) + 1
st.caption(f"run #{st.session_state['run_count']} at {time.strftime('%H:%M:%S')}")

# CookieManager は key を固定して重複エラーを防止
cm = stx.CookieManager(key="cm_minimal")

# ===== 現在の Cookie 一覧 =====
st.subheader("現在の Cookie 一覧")
cookies = {}
try:
    cookies = cm.get_all()  # 対応バージョンなら全取得
except Exception:
    pass
if cookies:
    st.json(cookies)
else:
    st.write("（Cookie はまだ見つかりません）")

st.divider()

# ===== フォームで一括送信（ウィジェット操作での都度 rerun を防ぐ）=====
st.subheader("Set / Get / Delete（フォーム送信）")
with st.form("cookie_form", clear_on_submit=False):
    c_name = st.text_input("Cookie名", value="test_cookie_min", key="min_name")
    c_val  = st.text_input("Cookie値", value=f"val_{int(time.time())}", key="min_val")
    c_max  = st.number_input("Max-Age（秒）", min_value=0, value=60, step=10, key="min_max")
    c_path = st.text_input("Path", value="/", help="通常は / 推奨。同一ドメイン全体で共有されます。", key="min_path")

    col1, col2, col3 = st.columns(3)
    with col1:
        do_set = st.form_submit_button("Set（発行）", use_container_width=True)
    with col2:
        do_get = st.form_submit_button("Get（取得）", use_container_width=True)
    with col3:
        do_del = st.form_submit_button("Delete（削除）", use_container_width=True)

# ===== 結果はセッションに保持し、rerun 後も残す =====
msg = ""
err = ""

try:
    if do_set:
        # key は毎回ユニークにしないと Duplicate エラーになる
        kwargs = {}
        if c_path.strip():
            kwargs["path"] = c_path.strip()
        cm.set(
            c_name, c_val,
            max_age=int(c_max),
            same_site="Lax",
            key=f"min_set_{time.time()}",
            **kwargs
        )
        msg = f"✅ Set OK: {c_name}={c_val}（path={kwargs.get('path','<未指定>')}）"
        st.session_state["last_action"] = ("set", msg)

    elif do_get:
        v = cm.get(c_name)
        msg = f"ℹ️ Get: {c_name} -> {repr(v)}"
        st.session_state["last_action"] = ("get", msg)

    elif do_del:
        # 失効で確実に削除（path 指定を維持）
        path_for_del = c_path.strip() or "/"
        cm.set(c_name, "", max_age=0, path=path_for_del, key=f"min_expire_{time.time()}")
        msg = f"🗑️ Delete（失効）OK: {c_name}（path={path_for_del}）"
        st.session_state["last_action"] = ("del", msg)

except Exception as e:
    err = f"❌ 例外: {e}"
    st.session_state["last_action"] = ("error", err)

# ===== 直前の結果を必ず表示（rerun後も残る）=====
if "last_action" in st.session_state:
    kind, text = st.session_state["last_action"]
    if kind == "error":
        st.error(text)
    elif kind == "set":
        st.success(text)
    elif kind == "get":
        st.info(text)
    elif kind == "del":
        st.success(text)

st.divider()
st.markdown("""
### メモ
- **フォーム送信**にしたことで、入力中のたびに rerun されるのを防ぎ、結果が確実に残るようにしています。  
- `cm.set(..., key="min_set_タイムスタンプ")` のように **毎回ユニーク key** を付けて重複エラーを回避しています。  
- 反映が1リレンダー遅れる場合があります。上の「現在の Cookie 一覧」が更新されないときは、上部の🔁で再実行してください。  
- 必ず **Nginx 経由の URL（例: http://<ホスト>/login_test/）** で開いてください。直ポートアクセスは別サイト扱いになり、SSO検証の動きがズレます。
""")
