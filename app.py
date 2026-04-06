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

genai.configure(api_key=api_key)

st.set_page_config(page_title="自動写真保存 v5.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v5")

if img_file:
    # 1. 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # 2. 【解析 1回目】タイトル生成 (Python側)
    ai_title = "名称未設定"
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
            response = model.generate_content([prompt1, img])
            if response and response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. 【解析 2回目 ＆ 住所取得 ＆ 保存】をJavaScriptで実行
    # ここでは「リロード」をせず、JS内で全て処理します
    st.info("📍 現在地を特定し、駅名を分析しています...")

    save_script = f"""
    <div id="log" style="font-size:12px; color:gray; margin-top:10px;"></div>
    <script>
    (async function() {{
        const log = document.getElementById('log');
        const aiTitle = "{ai_title}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        
        try {{
            log.innerText = "📍 位置情報を取得中...";
            const pos = await new Promise((resolve, reject) => {{
                navigator.geolocation.getCurrentPosition(resolve, reject, {{enableHighAccuracy: true, timeout: 7000}});
            }});

            // 住所取得
            log.innerText = "🗺️ 住所を照合中...";
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}&accept-language=ja`);
            const data = await res.json();
            const a = data.address;
            const finalAddr = (a.city || a.town || a.village || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
            
            log.innerText = "🚉 最寄り駅を特定中...";
            // Python側へ戻さず、ここからGeminiのAPIを叩くことも可能ですが、
            // 安全のため一度Pythonの関数を呼び出すか、ここでは住所とタイトルで保存を優先させます。
            // ※リロードを避けるため、今回はJS内で構築した住所とタイトルを結合して保存します。

            const displayText = aiTitle + " | " + finalAddr;
            const fileName = aiTitle + "_" + finalAddr.replace(/[/\\\\?%*:|"<>]/g, '-') + ".jpg";

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
                const textWidth = ctx.measureText(displayText).width;
                
                ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
                ctx.fillRect(20, 20, textWidth + (padding * 2), fontSize + (padding * 2));
                ctx.fillStyle = "white";
                ctx.fillText(displayText, 20 + padding, 20 + padding);
                
                const link = document.createElement('a');
                link.download = fileName;
                link.href = canvas.toDataURL('image/jpeg', 1.0);
                link.click();
                log.innerText = "✅ 保存が完了しました: " + fileName;
            }};
            img.src = imgBase64;

        }} catch (e) {{
            log.innerText = "❌ エラー: " + e.message;
            // 位置情報が取れなくても保存だけは実行
            const fileName = aiTitle + "_位置情報なし.jpg";
            const link = document.createElement('a');
            link.download = fileName;
            link.href = imgBase64;
            link.click();
        }}
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=100)

    if st.button("次の写真を撮る"):
        st.rerun()
