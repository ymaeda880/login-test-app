# login_test_app/pages/03_クッキー診断.py
from __future__ import annotations
import time
import json
import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(page_title="Cookie 診断", page_icon="🍪", layout="centered")
st.title("🍪 Cookie 診断ページ（extra-streamlit-components）")

cm = stx.CookieManager()

# --- 初回ウォームアップ（CookieManagerは初回レンダで空になることがある） ---
if "cookie_warmup_done" not in st.session_state:
    st.session_state.cookie_warmup_done = True
    st.info("⏳ Cookieウォームアップ中…（1回だけ自動再実行）")
    st.rerun()

# --- 参考情報 ---
st.caption("現在のURLクエリ:")
try:
    st.code(json.dumps(dict(st.query_params), ensure_ascii=False, indent=2))
except Exception as e:
    st.write("query_params取得でエラー:", e)

st.divider()

# === 現在のCookie一覧 ===
st.subheader("現在のCookie一覧")
cookies_dict = {}
try:
    # 0.1.8x 系には get_all() がある想定。無い場合は既知キーだけ拾う（下の except）
    cookies_dict = cm.get_all()  # type: ignore
except Exception:
    # フォールバック：代表的なキーだけ確認
    for k in ["prec_sso", "pw_input", "user_input", "do_login", "flash_login_ok", "test_cookie"]:
        v = cm.get(k)
        if v is not None:
            cookies_dict[k] = v

if cookies_dict:
    st.json(cookies_dict)
else:
    st.write("（Cookieは見つかりませんでした）")

st.divider()

# === 単発テスト：set / get / delete ===
st.subheader("単発テスト：Cookie を手動で set/get/delete")

c_name = st.text_input("Cookie名", value="test_cookie", key="cname")
c_val  = st.text_input("Cookie値", value=f"val_{int(time.time())}", key="cval")
c_max  = st.number_input("Max-Age（秒）", min_value=0, value=60, step=10, help="0で即時失効=削除相当")
c_path = st.text_input("Path（空なら未指定）", value="/", help='通常は "/" 推奨。未指定だと現在パスに限定されることがあります。')

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Set（発行）", key="btn_set_cookie"):
        kwargs = {}
        if c_path.strip():
            kwargs["path"] = c_path.strip()
        # key は重複禁止：都度ユニーク
        cm.set(c_name, c_val, max_age=int(c_max), same_site="Lax", key=f"set_{c_name}_{time.time()}", **kwargs)
        st.success(f"Set OK: {c_name}={c_val}（path={kwargs.get('path','<未指定>')}）")
        st.info("※ 直後は一覧に反映されないことがあります。もう一度実行/リロードしてください。")

with col2:
    if st.button("Get（取得）", key="btn_get_cookie"):
        v = cm.get(c_name)
        st.write(f"Get: {c_name} -> {repr(v)}")

with col3:
    if st.button("Delete（削除）", key="btn_del_cookie"):
        # バージョン差異対策：delete(path=) が無い版もあるので try/except
        try:
            if c_path.strip():
                cm.delete(c_name, path=c_path.strip())
            else:
                cm.delete(c_name)
        except TypeError:
            # 失効で上書き（確実）
            if c_path.strip():
                cm.set(c_name, "", max_age=0, path=c_path.strip(), key=f"expire_{c_name}_{time.time()}")
            else:
                cm.set(c_name, "", max_age=0, key=f"expire_{c_name}_{time.time()}")
        st.success(f"Delete（失効）OK: {c_name}")

st.divider()

# === 代表ケースのショートカット ===
st.subheader("代表ケースのショートカット")

cc1, cc2, cc3 = st.columns(3)
with cc1:
    if st.button("prec_sso を / で発行（8h）", key="sso_issue"):
        cm.set("prec_sso", f"dummy_{int(time.time())}", max_age=8*3600, path="/", same_site="Lax",
               key=f"set_prec_sso_{time.time()}")
        st.success("発行しました（path=/, 8時間）")

with cc2:
    if st.button("prec_sso を / で削除", key="sso_del_root"):
        # 失効で確実に削除
        cm.set("prec_sso", "", max_age=0, path="/", key=f"expire_prec_sso_root_{time.time()}")
        st.success("削除しました（path=/）")

with cc3:
    if st.button("prec_sso を 現在パス で削除", key="sso_del_default"):
        cm.set("prec_sso", "", max_age=0, key=f"expire_prec_sso_default_{time.time()}")
        st.success("削除しました（path=未指定=現在パス）")

st.divider()

# === Nginx越しの注意点 ===
st.subheader("Nginx 越しでの注意")
st.markdown("""
- **同一ドメイン/同一ポート**であれば Cookie は共有されます。\
  例：`http://prec.local/auth_portal/` と `http://prec.local/login_test/`。
- ブラウザは **ポートが違うと別サイト扱い**にします。直ポート（:8591 と :8592）を混ぜると \
  Cookie が片方に残っているように見えるので、Nginx経由に統一してください。
- `path="/"` で発行/削除すると、同ドメイン配下の**全パス**で共有/無効化できます。
""")

st.divider()

# === デバッグパネル ===
with st.expander("デバッグ（内部状態）"):
    st.write("cookie_warmup_done:", st.session_state.get("cookie_warmup_done"))
    try:
        st.write("cm.get_all():", cm.get_all())
    except Exception as e:
        st.write("get_all() 例外:", e)
    st.write("個別 get 調査:", {k: cm.get(k) for k in ["prec_sso", "test_cookie", "pw_input", "user_input", "do_login", "flash_login_ok"]})

st.caption("Tip: 発行直後は CookieManager が値を返すまで 1 リレンダー必要なことがあります。上のボタンを再度押すか、ページを更新してください。")
