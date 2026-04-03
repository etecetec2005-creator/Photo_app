import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import requests

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真保存アプリ", layout="centered")
st.title("写真解析・撮影")

# セッション状態の初期化
if "img_state" not in st.session_state:
    st.session_state.img_state = None

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    st.session_state.img_state = Image.open(img_file)

if st.session_state.img_state:
    img = st.session_state.img_state
    st.image(img, caption="解析前の確認")

    if st.button("住所とタイトルを自動生成", type="primary"):
        with st.spinner("AIと通信中..."):
            
            # --- 1. 住所取得（別の予備APIを使用） ---
            address = "不明な場所"
            try:
                # ip-api.com を使用（よりシンプルなレスポンス）
                res = requests.get("http://ip-api.com/json/?lang=ja", timeout=5).json()
                if res.get("status") == "success":
                    address = f"{res.get('city', '')}{res.get('district', '')}"
                if not address: address = "不明な地域"
            except:
                address = "場所特定エラー"

            # --- 2. Gemini 解析（モデル指定を修正） ---
            title = "名称未設定"
            try:
                # モデル名を正式なフルパス形式に変更
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                prompt = "この写真を分析し、ふさわしい日本語の短いタイトル（20文字以内）を1つだけ出力してください。記号や句読点は含めないでください。"
                
                response = model.generate_content([prompt, img])
                if response.text:
                    title = response.text.strip().replace(" ", "").replace("　", "").replace("。", "")
            except Exception as e:
                st.error(f"AI解析に失敗しました。理由: {str(e)}")

            # --- 3. 保存用ファイル名の確定 ---
            # ファイル名に使えない文字を削除
            filename = f"{address}_{title}.jpg".replace("/", "-")
            
            st.success("生成が完了しました！")
            st.write(f"📍 取得住所: **{address}**")
            st.write(f"🏷️ 生成タイトル: **{title}**")
            
            # ダウンロードボタン
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            
            st.download_button(
                label=f"📁 「{filename}」として保存",
                data=buf.getvalue(),
                file_name=filename,
                mime="image/jpeg",
                use_container_width=True
            )

    if st.button("撮り直す"):
        st.session_state.img_state = None
        st.rerun()
