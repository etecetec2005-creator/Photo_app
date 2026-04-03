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
st.title("📸 写真解析・確定保存")

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
                prompt = "この写真の内容を分析し、短いタイトルを1つ。結果のみ。"
                response = model.generate_content([prompt, img])
                if response.text:
                    ai_title_value = response.text.strip().replace("\n", "").replace("/", "-")
                    st.success(f"🏷️ AIタイトル: {ai_title_value}")
        except:
            ai_title_value = "名称未設定"

    if ai_title_value:
        # 画像をBase64変換（PDFに埋め込む用）
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        address_script = f"""
        <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px; margin-bottom:10px;">
            住所取得中...
        </div>
        <button id="pdf-btn" style="width:100%; padding:15px; background-color:#1a73e8; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:16px;">
            📄 名前を維持してPDF保存
        </button>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

        <script>
        const output = document.getElementById('address-out');
        const pdfBtn = document.getElementById('pdf-btn');
        const aiTitle = "{ai_title_value}";
        const imgData = "data:image/jpeg;base64,{img_str}";

        navigator.geolocation.getCurrentPosition(
            async (pos) => {{
                try {{
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                        headers: {{ 'Accept-Language': 'ja' }}
                    }});
                    const data = await response.json();
                    const addr = data.address;
                    let finalAddr = (addr.city || "") + (addr.suburb || "") + (addr.city_district || "");
                    if(!finalAddr) finalAddr = "住所不明";
                    
                    output.innerText = finalAddr;
                    const fileName = finalAddr + "_" + aiTitle + ".pdf";
                    pdfBtn.innerText = "📄 「" + fileName + "」を保存";

                    pdfBtn.onclick = async () => {{
                        const {{ jsPDF }} = window.jspdf;
                        const doc = new jsPDF();
                        
                        // 画像をPDFのサイズに合わせて配置
                        doc.text(finalAddr + " / " + aiTitle, 10, 10);
                        doc.addImage(imgData, 'JPEG', 10, 20, 180, 135);
                        
                        // PDFとして保存（これならiOSでも名前が維持されます）
                        doc.save(fileName);
                    }};

                }} catch (err) {{ output.innerText = "エラー"; }}
            }},
            (err) => {{ output.innerText = "位置情報オフ"; }},
            {{ enableHighAccuracy: true }}
        );
        </script>
        """
        components.html(address_script, height=200)

    if st.button("撮り直す"):
        st.rerun()
