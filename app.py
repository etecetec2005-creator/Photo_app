import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import base64

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。StreamlitのSecretsに登録してください。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="自動写真保存 v5.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v50")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # --- ステップ①: Python側でタイトル生成 (1回目AI) ---
    ai_title = "名称未設定"
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
            response = model.generate_content([prompt1, img])
            if response and response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except:
            pass

    # 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # --- ステップ②: JavaScript側で [住所取得] → [2回目AI(駅名)] → [保存] をリロードなしで実行 ---
    st.info("📍 住所と駅名を特定しています。このままお待ちください...")

    # JavaScript内にAPIキーを埋め込むため、安全に処理
    save_script = f"""
    <div id="js_log" style="font-size:13px; color:#555; padding:15px; background:#f0f2f6; border-radius:10px; border:1px solid #ddd; line-height:1.6;">
        🚀 処理を開始しました...
    </div>
    <script>
    (async function() {{
        const log = document.getElementById('js_log');
        const API_KEY = "{api_key}";
        const aiTitle = "{ai_title}";
        const imgBase = "data:image/jpeg;base64,{img_str}";
        
        try {{
            // 1. 位置情報取得
            log.innerHTML = "📍 <b>位置情報を取得中...</b><br>ブラウザの許可ダイアログが出た場合は「許可」してください。";
            const pos = await new Promise((res, rej) => {{
                navigator.geolocation.getCurrentPosition(res, rej, {{enableHighAccuracy: true, timeout: 8000}});
            }});
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;

            // 2. 住所取得 (OSM Nominatim)
            log.innerHTML = "🗺️ <b>住所を照合中...</b>";
            const addrRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{lat}}&lon=${{lon}}&accept-language=ja`);
            const addrData = await addrRes.json();
            const a = addrData.address;
            const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.neighbourhood || "");

            // 3. 2回目AI解析 (リロードを避けるため、ブラウザから直接Gemini APIを叩く)
            log.innerHTML = "🚉 <b>住所「" + finalAddr + "」から最寄り駅を特定中...</b>";
            const geminiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + API_KEY;
            
            const geminiRes = await fetch(geminiUrl, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    contents: [{{ parts: [{{ text: "住所「" + finalAddr + "」に最も近い実在する駅名を1つだけ答えてください。駅名のみ出力。" }}] }}]
                }})
            }});
            const geminiData = await geminiRes.json();
            const station = geminiData.candidates[0].content.parts[0].text.trim().replace(/\\n/g, "");

            // 4. 画像合成と保存
            log.innerHTML = "💾 <b>画像を生成して保存しています...</b><br>駅名: " + station;
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
                const tw = ctx.measureText(displayText).width;
                
                // 文字背景
                ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
                ctx.fillRect(20, 20, tw + fontSize, fontSize * 1.5);
                
                // 文字
                ctx.fillStyle = "white";
                ctx.fillText(displayText, 20 + (fontSize/2), 20 + (fontSize/4));
                
                // 保存用リンク作成
                const link = document.createElement('a');
                link.download = fileName;
                link.href = canvas.toDataURL('image/jpeg', 0.95);
                link.click();
                log.innerHTML = "<b style='color:green; font-size:16px;'>✅ 保存完了しました！</b><br>ファイル名: " + fileName;
            }};
            img.src = imgBase;

        }} catch (e) {{
            log.innerHTML = "<b style='color:red;'>❌ 中断されました</b><br>理由: " + e.message + "<br>※位置情報がオフ、またはタイムアウトした可能性があります。";
            // 失敗時もタイトルのみで保存を実行
            const link = document.createElement('a');
            link.download = aiTitle + "_住所不明.jpg";
            link.href = imgBase;
            link.click();
        }}
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=180)

    if st.button("リセットして次の写真を撮る"):
        st.rerun()
