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

st.set_page_config(page_title="写真解析保存", layout="centered")
st.title("📸 写真解析・自動保存")

img_file = st.camera_input("写真を撮る")

if img_file:
    # 1. 画像読み込み
    raw_img = Image.open(img_file)
    st.image(raw_img, caption="解析中...")

    # 2. AIタイトル生成
    ai_title = "名称未設定"
    with st.spinner("AI解析中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
            model = genai.GenerativeModel(target_model)
            response = model.generate_content(["この写真を一言で表す短い日本語タイトルを付けて。結果のみ。", raw_img])
            if response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-")
        except:
            pass

    # 3. 住所とタイトルを「画像」として合成（文字化け対策）
    # ※iPhoneで日本語を刻むため、少し大きめの余白を作ります
    def create_labeled_img(base_img, text):
        width, height = base_img.size
        # 下部に白帯を追加
        new_img = Image.new('RGB', (width, height + 120), (255, 255, 255))
        new_img.paste(base_img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        # フォント設定（標準フォントを使用）
        try:
            # Linux/StreamlitCloud環境用のフォントパス
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((20, height + 20), text, fill=(0, 0, 0), font=font)
        return new_img

    # 4. JavaScriptでPDFを生成して即ダウンロード
    # 画像をBase64化
    buffered = io.BytesIO()
    raw_img.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    st.success(f"解析完了: {ai_title}")

    # 住所取得 -> PDF生成 -> 保存までを最短で走らせるJS
    auto_save_script = f"""
    <div id="status" style="font-weight:bold; color:#1a73e8;">📍 現在地を確認して保存します...</div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script>
    (async function() {{
        const status = document.getElementById('status');
        const imgData = "data:image/jpeg;base64,{img_str}";
        const aiTitle = "{ai_title}";

        navigator.geolocation.getCurrentPosition(async (pos) => {{
            try {{
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                    headers: {{ 'Accept-Language': 'ja' }}
                }});
                const data = await res.json();
                const addr = data.address;
                const finalAddr = (addr.city || "") + (addr.suburb || "") + (addr.city_district || "") + (addr.neighbourhood || "") || "住所不明";
                
                const fileName = finalAddr + "_" + aiTitle + ".pdf";
                
                const {{ jsPDF }} = window.jspdf;
                const doc = new jsPDF('p', 'mm', 'a4');
                
                // PDFの中身（文字化けしないように、ここでもテキストを追加）
                doc.setFontSize(16);
                doc.text(aiTitle, 15, 20);
                doc.setFontSize(10);
                doc.text(finalAddr, 15, 30);
                
                // 画像を貼り付け
                doc.addImage(imgData, 'JPEG', 15, 40, 180, 135);
                
                // 保存実行
                doc.save(fileName);
                status.innerText = "✅ 保存を開始しました: " + fileName;

            }} catch (e) {{
                status.innerText = "⚠️ 保存エラーが発生しました";
            }}
        }}, (err) => {{
            status.innerText = "❌ 位置情報を許可してください";
        }}, {{enableHighAccuracy: true}});
    }})();
    </script>
    """
    st.components.v1.html(auto_save_script, height=100)

    if st.button("次の写真を撮る"):
        st.rerun()
