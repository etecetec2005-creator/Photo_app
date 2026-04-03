import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import os

# --- セキュリティ設定（環境変数から取得） ---
# Streamlit CloudのSecrets、またはローカルの環境変数から取得します
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("APIキーが設定されていません。StreamlitのSecrets設定を確認してください。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力（iPhone SE などのモバイル端末でも使いやすいUI）
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    with st.spinner("AIが解析中..."):
        try:
            # 利用可能な最新モデルを動的に取得（404エラー対策）
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # gemini-1.5-flashを最優先、なければリストの先頭を使用
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力してください。"
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success(f"🏷️ タイトル: {response.text.strip()}")
                else:
                    st.warning("タイトルを生成できませんでした。")
            else:
                st.error("利用可能なAIモデルが見つかりませんでした。")
                
        except Exception as e:
            st.error("解析エラーが発生しました。")
            st.code(f"Detail: {str(e)}")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 住所取得ロジック（都道府県抜き）
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const addr = data.address;
                let formattedAddress = "";
                if (addr.city) formattedAddress += addr.city;
                if (addr.suburb) formattedAddress += addr.suburb;
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                output.innerText = formattedAddress || "住所特定失敗";
            } catch (err) { output.innerText = "通信エラー"; }
        },
        (err) => { output.innerText = "位置情報オフ"; },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押ししてください。")
    
    if st.button("撮り直す"):
        st.rerun()
