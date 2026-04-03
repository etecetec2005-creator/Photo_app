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

st.set_page_config(page_title="写真解析・保存", layout="centered")
st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影された写真")

    # 解析実行ボタン（このボタンを押したタイミングで全てを確定させる）
    if st.button("AIタイトル作成と住所取得を実行"):
        
        # 1. 住所取得 (ブラウザからではなく、簡易的なIPベースかセッションで管理)
        # ※js_evalの競合を避けるため、ここでは標準的な方法で試行します
        address_name = "不明な場所"
        with st.spinner("現在地を確認中..."):
            try:
                # 緯度経度が取れない場合のフォールバックとしてIPから取得
                geo_req = requests.get("https://ipapi.co/json/").json()
                address_name = geo_req.get("city", "地域不明")
            except:
                address_name = "場所特定失敗"

        # 2. Gemini 解析
        ai_title = "名称未設定"
        with st.spinner("AIがタイトルを生成中..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "この写真の内容を20文字以内の日本語で短いタイトルにして。記号・スペース・句読点は一切含めないで。結果のみ出力。"
                response = model.generate_content([prompt, img])
                if response.text:
                    ai_title = response.text.strip().replace(" ", "").replace("　", "").replace("。", "")
            except Exception as e:
                st.error(f"AI解析エラー: {e}")

        # 3. 結果表示と保存準備
        final_filename = f"{address_name}_{ai_title}.jpg"
        st.success(f"✅ 生成完了！")
        st.write(f"📍 住所要素: {address_name}")
        st.write(f"🏷️ タイトル: {ai_title}")
        st.info(f"📁 保存名: {final_filename}")

        # ダウンロードボタン
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        st.download_button(
            label="この名前で保存（ダウンロード）",
            data=buf.getvalue(),
            file_name=final_filename,
            mime="image/jpeg",
            use_container_width=True
        )

if st.button("リセット"):
    st.rerun()
