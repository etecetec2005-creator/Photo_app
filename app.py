import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import os
import base64

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析", layout="centered")
st.title("写真解析・撮影")

img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    ai_title_value = "" 
    with st.spinner("AIがタイトルを生成中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを1つだけ付けてください。結果のみを出力。"
                response = model.generate_content([prompt, img])
                
                if response.text:
                    ai_title_value = response.text.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "").replace("/", "-")
                    st.success(f"🏷️ AIタイトル: {ai_title_value}")
        except Exception as e:
            st.error(f"解析エラー: {e}")

    if ai_title_value:
        st.write("---")
        
        # 画像をBase64変換
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 住所取得 + 別タブ表示処理
        address_script = f"""
        <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px; margin-bottom:10px;">
            位置情報を取得中...
        </div>
        <button id="view-btn" style="width:100%; padding:15px; background-color:#2e7d32; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:16px;">
            ⌛ 準備中...
        </button>

        <script>
        const output = document.getElementById('address-out');
        const viewBtn = document.getElementById('view-btn');
        const finalAiTitle = "{ai_title_value}";
        const imgData = "data:image/jpeg;base64,{img_str}";

        navigator.geolocation.getCurrentPosition(
            async (pos) => {{
                try {{
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                        headers: {{ 'Accept-Language': 'ja' }}
                    }});
                    const data = await response.json();
                    const addr = data.address;
                    let formattedAddress = "";
                    if (addr.city) formattedAddress += addr.city;
                    if (addr.suburb) formattedAddress += addr.suburb;
                    if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                    if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                    
                    const finalAddr = (formattedAddress || "住所特定失敗").replace(/[/\\?%*:|"<>]/g, '-');
                    output.innerText = finalAddr;

                    const fileName = finalAddr + "_" + finalAiTitle + ".jpg";
                    viewBtn.innerText = "📂 名前付きで保存用の画面を開く";
                    
                    viewBtn.onclick = () => {{
                        // 新しいタブで画像を表示
                        const newTab = window.open();
                        newTab.document.write('<html><head><title>' + fileName + '</title></head><body style="margin:0; display:flex; flex-direction:column; align-items:center; background:#000; color:#fff; font-family:sans-serif;">');
                        newTab.document.write('<p style="padding:20px; text-align:center;">画像を長押しして<b>「"ファイル"に保存」</b>を選択してください<br><small>保存名: ' + fileName + '</small></p>');
                        newTab.document.write('<img src="' + imgData + '" style="max-width:100%; height:auto;">');
                        newTab.document.write('</body></html>');
                        newTab.document.close();
                    }};

                }} catch (err) {{ 
                    output.innerText = "住所取得エラー";
                }}
            }},
            (err) => {{ output.innerText = "位置情報を許可してください"; }},
            {{ enableHighAccuracy: true }}
        );
        </script>
        """
        components.html(address_script, height=220)

    if st.button("撮り直す"):
        st.rerun()
