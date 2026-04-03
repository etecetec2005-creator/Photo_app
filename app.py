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
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 住所取得 + 強力なダウンロード処理
        address_script = f"""
        <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px; margin-bottom:10px;">
            位置情報を取得中...
        </div>
        <button id="dl-btn" style="width:100%; padding:15px; background-color:#ff4b4b; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            📥 準備中...
        </button>

        <script>
        const output = document.getElementById('address-out');
        const dlBtn = document.getElementById('dl-btn');
        const finalAiTitle = "{ai_title_value}";
        const base64Data = "{img_str}";

        // Base64をBlob(ファイルオブジェクト)に変換する関数
        function base64ToBlob(base64, type) {{
            const bin = atob(base64);
            const buffer = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) {{
                buffer[i] = bin.charCodeAt(i);
            }}
            return new Blob([buffer.buffer], {{type: type}});
        }}

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
                    dlBtn.innerText = "📥 「" + fileName + "」を保存";
                    
                    dlBtn.onclick = () => {{
                        const blob = base64ToBlob(base64Data, 'image/jpeg');
                        const url = window.URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = fileName;
                        
                        // iPhone/Safari対策: ボディに追加してクリック
                        document.body.appendChild(link);
                        link.click();
                        
                        // クリーンアップ
                        setTimeout(() => {{
                            document.body.removeChild(link);
                            window.URL.revokeObjectURL(url);
                        }}, 100);
                    }};

                }} catch (err) {{ 
                    output.innerText = "住所取得エラー";
                    dlBtn.innerText = "📥 住所なしで保存";
                }}
            }},
            (err) => {{ output.innerText = "位置情報を許可してください"; }},
            {{ enableHighAccuracy: true }}
        );
        </script>
        """
        components.html(address_script, height=200)

    if st.button("撮り直す"):
        st.rerun()
