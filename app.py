import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io

# --- Gemini API 設定 ---
API_KEY = "AIzaSyAC6W0cwPmw3VrpxqXoiKZEv4CpIYUHME0"
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    with st.spinner("AIが最適なモデルを探して解析中..."):
        try:
            # 利用可能なモデルをリストアップし、画像処理ができるものを自動選択
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 優先順位：1.5 Flash -> 1.5 Pro -> その他
            target_model = None
            for m_name in available_models:
                if 'gemini-1.5-flash' in m_name:
                    target_model = m_name
                    break
            
            if not target_model and available_models:
                target_model = available_models[0]

            if target_model:
                model = genai.GenerativeModel(target_model)
                prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力してください。"
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success(f"🏷️ タイトル: {response.text.strip()}")
                else:
                    st.warning("解析結果が空でした。")
            else:
                st.error("利用可能なAIモデルが見つかりませんでした。")
                
        except Exception as e:
            st.error(f"解析エラーが発生しました。")
            st.code(f"Error: {str(e)}")

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
        (err) => { output.innerText = "位置情報を許可してください"; },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして保存してください。")
    
    if st.button("撮り直す"):
        st.rerun()
