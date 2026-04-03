import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
from streamlit_js_eval import streamlit_js_eval

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析・自動命名保存", layout="centered")
st.title("写真解析・撮影")

# --- 1. 位置情報の取得 (JavaScriptからPythonへ値を渡す) ---
# 住所を特定するための緯度経度を取得
location = streamlit_js_eval(js_expressions="new Promise((res, rej) => { navigator.geolocation.getCurrentPosition(pos => res(pos.coords), err => res(null)) })", key="loc")

address_name = "位置情報不明"
if location:
    # 緯度経度から住所を逆ジオコーディング（Python側で実行）
    import requests
    try:
        lat, lon = location['latitude'], location['longitude']
        geo_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", 
                               headers={'Accept-Language': 'ja', 'User-Agent': 'StreamlitApp'}).json()
        addr = geo_res.get('address', {})
        # 市町村以下の住所を構築
        address_name = (addr.get('city') or addr.get('town') or "") + (addr.get('suburb') or addr.get('neighbourhood') or "")
        if not address_name: address_name = "不明な場所"
    except:
        address_name = "住所取得エラー"

# --- 2. カメラ入力 ---
img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption=f"📍 現在地付近: {address_name}")

    # --- Gemini 解析 ---
    ai_title = "タイトル未生成"
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "この写真の内容を分析し、ファイル名に使える20文字以内の日本語で短いタイトルを付けてください。記号やスペースは含めないでください。結果のみを出力してください。"
            response = model.generate_content([prompt, img])
            if response.text:
                ai_title = response.text.strip().replace(" ", "").replace("　", "")
                st.success(f"🏷️ AIタイトル: {ai_title}")
        except Exception as e:
            st.error("AI解析失敗")

    # --- 3. ファイル名の作成と保存設定 ---
    # 禁止文字を置換
    safe_address = address_name.replace("/", "_")
    final_filename = f"{safe_address}_{ai_title}.jpg"

    # ダウンロード用バッファの作成
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    byte_im = buf.getvalue()

    st.write(f"📁 保存名: `{final_filename}`")
    
    # ダウンロードボタン
    st.download_button(
        label="この名前で写真を保存",
        data=byte_im,
        file_name=final_filename,
        mime="image/jpeg",
        use_container_width=True
    )

    if st.button("撮り直す"):
        st.rerun()
