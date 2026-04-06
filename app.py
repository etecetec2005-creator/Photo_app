import streamlit as st
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

# Python側でも念のため設定
genai.configure(api_key=api_key)

st.set_page_config(page_title="自動写真保存 v4.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v4")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # --- ステップ①: Python側でタイトル生成 (1回目AI) ---
    ai_title = "名称未設定"
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の10文字以内の日本語タイトルを1つだけ出力してください。"
            response = model.generate_content([prompt1, img])
            if response and response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except:
            pass

    # 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # --- ステップ②: JavaScript側で [住所取得] → [2回目AI(駅名)] → [保存] を一気に実行 ---
    # リロードを挟まないため、ブラウザ内でGemini APIを直接叩く特殊な構成です
    st.info("📍 住所と駅名を特定しています。画面をそのままにしてください...")

    save_script = f"""
    <div id="js_log" style="font-size:13px; color:#666; padding:10px; background:#f9f9f9; border-radius:5px; border:1px solid #ddd;">
        ⏳ 処理を開始します...
    </div>
    <script>
    (async function() {{
        const log = document.getElementById('js_log');
        const API_KEY = "{api_key}";
        const aiTitle = "{ai_title}";
        const imgBase = "data:image/jpeg;base64,{img_str}";
        
        try {{
            // 1. 位置情報取得
            log.innerText = "📍 位置情報を取得中...";
            const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;

            // 2. 住所取得 (OSM)
            log.innerText = "🗺️ 住所を照合中...";
            const addrRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{lat}}&lon=${{lon}}&accept-language=ja`);
            const addrData = await addrRes.json();
            const a = addrData.address;
            const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.neighbourhood || "");

            // 3. 2回目AI解析 (ブラウザから直接Geminiを叩く)
            log.innerText = "🚉 住所「" + finalAddr + "」から最寄り駅を特定中...";
            const geminiRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${{API_KEY}}`, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    contents: [{{ parts: [{{ text: "住所「" + finalAddr + "」に最も近い実在する駅名を1つだけ答えてください。余計な説明は一切不要。駅名のみ出力。" }}] }}]
                }})
            }});
            const geminiData = await geminiRes.json();
            const station = geminiData.candidates[0].content.parts[0].text.trim().replace(/\\n/g, "");

            // 4. 画像合成と保存
            log.innerText = "💾 保存を実行中: " + station;
            const displayText = aiTitle + " | " + finalAddr + " | " + station;
            const fileName = aiTitle + "_" + finalAddr.replace(/[/\\\\?%*:|"<>]/g, '-') + "_" + station + ".jpg";

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.onload = function() {{
                canvas.width = {width};
                canvas.height = {height};
                ctx.drawImage(img, 0, 0, {width}, {height});
                const fontSize = Math.floor({height} / 30);
                ctx.font = "bold " + fontSize + "px sans-serif";
                ctx.textBaseline = "top";
                const padding = fontSize / 2;
                const tw = ctx.measureText(displayText).width;
                ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
                ctx.fillRect(20, 20, tw + (padding * 2), fontSize + (padding * 2));
                ctx.fillStyle = "white";
                ctx.fillText(displayText, 20 + padding, 20 + padding);
                
                const link = document.createElement('a');
                link.download = fileName;
                link.href = canvas.toDataURL('image/jpeg', 0.9);
                link.click();
                log.innerHTML = "<b style='color:green;'>✅ 完了: " + fileName + "</b>";
            }};
            img.src = imgBase;

        }} catch (e) {{
            log.innerHTML = "<b style='color:red;'>❌ エラー: " + e.message + "</b>";
            // 失敗時も画像だけは出す
            const link = document.createElement('a');
            link.download = aiTitle + "_error.jpg";
            link.href = imgBase;
            link.click();
        }}
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=120)

    if st.button("次の写真を撮る"):
        st.rerun()
