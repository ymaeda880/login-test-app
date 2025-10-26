# login_test_app/pages/02_公開テスト.py
from __future__ import annotations
import streamlit as st
import extra_streamlit_components as stx
from lib.sso import verify_token  # 有効なら dict、無効/期限切れは None

st.set_page_config(page_title="公開ページ", page_icon="🌐")
st.title("🌐 公開（ログイン不要）")

cm = stx.CookieManager()
token = cm.get("prec_sso")
payload = verify_token(token) if token else None

if payload:
    user = payload.get("sub", "unknown")
    st.success(f"（任意）ログイン中のユーザー: **{user}**")
    with st.expander("🔎 JWT payload（検証済み）", expanded=False):
        st.write(payload)
else:
    st.info("未ログインでも閲覧できます。ログインしていればユーザー名を表示します。")

st.write("このページはログインなしでアクセス可能です。")
