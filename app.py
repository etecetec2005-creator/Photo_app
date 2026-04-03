import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="自動写真保存", layout="centered")
st.title("📸 全自動・写真解析保存")

img_file = st.camera_input("写真を撮る")

if img_file:
    # 1. 画像の読み込み
    img = Image.open(img_file)
    st.image(img, caption="解析・保存中...")

    # 2. AI解析（タイトル生成）
    ai_title = "名称未設定"
    with st.spinner("AIが解析しています..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
            model = genai.GenerativeModel(target_model)
            prompt = "この写真の内容を分析し、短い日本語タイトル（15文字以内）を1つ。結果のみ。"
            response = model.generate_content([prompt, img])
            if response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-")
        except:
            pass

    # 3. PDF生成用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. 全自動JavaScript（住所取得完了後に即保存）
    st.success(f"タイトル確定: {ai_title}")
    
    auto_save_script = f"""
    <div id="status" style="font-size:12px; color:gray; padding:5px;">位置情報を取得して自動保存します...</div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script>
    (async function() {{
        const status = document.getElementById('status');
        const aiTitle = "{ai_title}";
        const imgData = "data:image/jpeg;base64,{img_str}";

        navigator.geolocation.getCurrentPosition(
            async (pos) => {{
                try {{
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                        headers: {{ 'Accept-Language': 'ja' }}
                    }});
                    const data = await response.json();
                    const addr = data.address;
                    let finalAddr = (addr.city || "") + (addr.suburb || "") + (addr.city_district || "") + (addr.neighbourhood || "");
                    if(!finalAddr) finalAddr = "住所不明";
                    
                    const fileName = finalAddr + "_" + aiTitle + ".pdf";
                    status.innerText = "保存実行中: " + fileName;

                    // PDF生成
                    const {{ jsPDF }} = window.jspdf;
                    const doc = new jsPDF();
                    
                    // 文字化け回避のため、PDF内への日本語テキスト印字を最小限（または無し）にし、
                    // ファイル名に全力を注ぐ設定です。
                    doc.addImage(imgData, 'JPEG', 10, 20, 180, 135);
                    
                    // 自動保存実行
                    doc.save(fileName);
                    status.innerText = "✅ 保存完了しました";

                }} catch (err) {{ 
                    status.innerText = "住所取得エラーのため、名称未設定で保存します";
                    const doc = new window.jspdf.jsPDF();
                    doc.addImage(imgData, 'JPEG', 10, 20, 180, 135);
                    doc.save("不明な場所_" + aiTitle + ".pdf");
                }}
            }},
            (err) => {{ status.innerText = "位置情報を許可してください"; }},
            {{ enableHighAccuracy: true }}
        );
    }})();
    </script>
    """
    st.components.v1.html(auto_save_script, height=100)

    if st.button("次の写真を撮る"):
        st.rerun()
