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
st.title("📸 写真解析・PDF保存")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- 1. AI解析セクション ---
    ai_title_value = "" 
    with st.spinner("AIがタイトルを生成中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを1つだけ付けてください。結果のみを出力してください。"
                response = model.generate_content([prompt, img])
                
                if response.text:
                    # ファイル名に使えない文字を置換
                    ai_title_value = response.text.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "").replace("/", "-")
                    st.success(f"🏷️ AIタイトル: {ai_title_value}")
                else:
                    st.warning("タイトルを生成できませんでした。")
        except Exception as e:
            st.error(f"解析エラー: {e}")

    # --- 2. 住所取得 & PDF生成セクション ---
    if ai_title_value:
        st.write("---")
        st.subheader("📍 撮影場所と保存")

        # 画像をBase64変換
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 住所取得 + PDF保存スクリプト
        address_script = f"""
        <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px; margin-bottom:10px;">
            位置情報を取得中...
        </div>
        <button id="pdf-btn" style="width:100%; padding:15px; background-color:#1a73e8; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:16px;">
            📄 PDF保存の準備中...
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
                    let formattedAddress = "";
                    if (addr.city) formattedAddress += addr.city;
                    if (addr.suburb) formattedAddress += addr.suburb;
                    if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                    if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                    
                    const finalAddr = (formattedAddress || "住所特定失敗").replace(/[/\\?%*:|"<>]/g, '-');
                    output.innerText = finalAddr;

                    const fileName = finalAddr + "_" + aiTitle + ".pdf";
                    pdfBtn.innerText = "📄 「" + fileName + "」を保存";
                    
                    pdfBtn.onclick = () => {{
                        const {{ jsPDF }} = window.jspdf;
                        const doc = new jsPDF();
                        
                        // 画像をPDFに配置
                        doc.addImage(imgData, 'JPEG', 10, 20, 180, 135);
                        
                        // PDFとして保存
                        doc.save(fileName);
                    }};

                }} catch (err) {{ 
                    output.innerText = "住所取得エラー"; 
                    pdfBtn.innerText = "📄 住所なしでPDF保存";
                    pdfBtn.onclick = () => {{
                        const {{ jsPDF }} = window.jspdf;
                        const doc = new jsPDF();
                        doc.addImage(imgData, 'JPEG', 10, 20, 180, 135);
                        doc.save("不明な場所_" + aiTitle + ".pdf");
                    }};
                }}
            }},
            (err) => {{ 
                output.innerText = "位置情報を許可してください"; 
                pdfBtn.innerText = "PDF保存（位置情報なし）";
            }},
            {{ enableHighAccuracy: true }}
        );
        </script>
        """
        components.html(address_script, height=200)
    else:
        st.warning("AI解析待ち、または解析失敗のため保存ボタンを表示できません。")

    if st.button("撮り直す"):
        st.rerun()
