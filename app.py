import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import requests

# --- 設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析", layout="centered")
st.title("写真解析・撮影")

# セッション状態の初期化（画像を保持するため）
if "captured_img" not in st.session_state:
    st.session_state.captured_img = None

# カメラ入力
img_file = st.camera_input("写真を撮る")

# 新しく写真が撮られたらセッションに保存
if img_file:
    st.session_state.captured_img = Image.open(img_file)

# 写真が保持されている場合のみ、解析ボタンを表示
if st.session_state.captured_img:
    st.image(st.session_state.captured_img, caption="解析対象の画像")
    
    if st.button("住所取得とAI解析を実行", type="primary"):
        with st.spinner("処理中..."):
            
            # --- 1. 住所取得 (IPベース) ---
            address_name = "不明な場所"
            try:
                # User-Agentを設定してブロックを回避
                geo_res = requests.get("https://ipapi.co/json/", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if geo_res.status_code == 200:
                    data = geo_res.json()
                    # 市区町村を取得
                    address_name = data.get("city") or data.get("region") or "地域不明"
            except Exception as e:
                address_name = "場所特定失敗"

            # --- 2. Gemini 解析 ---
            ai_title = "名称未設定"
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "この写真のタイトルを日本語20文字以内で作成してください。記号や句読点は含めないでください。出力はタイトルのみ。"
                response = model.generate_content([prompt, st.session_state.captured_img])
                if response.text:
                    ai_title = response.text.strip().replace(" ", "").replace("　", "").replace("。", "")
            except Exception as e:
                st.error(f"AIエラー: {e}")

            # --- 3. 結果の表示と保存準備 ---
            final_filename = f"{address_name}_{ai_title}.jpg"
            
            st.success("解析完了！")
            st.write(f"📍 住所: **{address_name}**")
            st.write(f"🏷️ タイトル: **{ai_title}**")
            
            # ダウンロードボタン
            buf = io.BytesIO()
            st.session_state.captured_img.save(buf, format="JPEG")
            
            st.download_button(
                label=f"📁 {final_filename} を保存",
                data=buf.getvalue(),
                file_name=final_filename,
                mime="image/jpeg",
                use_container_width=True
            )

    if st.button("撮り直す"):
        st.session_state.captured_img = None
        st.rerun()
