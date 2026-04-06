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

st.set_page_config(page_title="自動写真保存 v2.7", layout="centered")
st.title("📸 写真解析 & 保存 (2段階AI)")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v27")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # --- ステップ①: AI解析 1回目（タイトル付与） ---
    ai_title = "名称未設定"
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。"
            response1 = model.generate_content([prompt1, img])
            if response1 and response1.text:
                ai_title = response1.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"タイトル解析エラー: {e}")

    # --- ステップ②: AI解析 2回目（駅名特定） ---
    # ※住所はこの後のJSで取得するため、ここでは画像のみから駅名を推測
    near_station = "駅名不明"
    with st.spinner("AIが最寄り駅を特定中..."):
        try:
            prompt2 = "この写真に写っている、または撮影場所として最も可能性の高い『実在する駅名』を1つだけ答えてください。不明なら『駅名不明』と答えてください。"
            response2 = model.generate_content([prompt2, img])
            if response2 and response2.text:
                near_station = response2.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"駅名特定エラー: {e}")

    # 3. 保存用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. JavaScriptで住所取得 ＋ 文字埋め込み ＋ 保存
    # ここで「タイトル」「駅名」をJSに渡し、現場で「住所」を合体させます
    st.success(f"解析完了: {ai_title} / {near_station}")
    
    save_script = f"""
    <div id="status_msg" style="font-size:12px; color:gray; padding:10px;">📍 現在地を取得して保存します...</div>
    <script>
    (async function() {{
        const status = document.getElementById('status_msg');
        const aiTitle = "{ai_title}";
        const station = "{near_station}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        const oW = {width};
        const oH = {height};

        // 位置情報の取得
        navigator.geolocation.getCurrentPosition(async (pos) => {{
            let finalAddr = "住所不明";
            try {{
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}&accept-language=ja`);
                if (res.ok) {{
                    const data = await res.json();
                    const a = data.address;
                    finalAddr = (a.city || a.town || a.village || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
                }}
            }} catch (e) {{
                console.error("Fetch failed", e);
                finalAddr = "住所取得エラー";
            }}
            saveImage(finalAddr);
        }}, (err) => {{
            saveImage("位置情報なし");
        }}, {{ timeout: 8000 }});

        function saveImage(addr) {{
            const displayText = aiTitle + " | " + addr + " | " + station;
            const fileName = aiTitle + "_" + addr.replace(/[/\\\\?%*:|"<>]/g, '-') + "_" + station + ".jpg";

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = function() {{
                canvas.width = oW;
                canvas.height = oH;
                ctx.drawImage(img, 0, 0, oW, oH);
                
                const fontSize = Math.floor(oH / 30); 
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
                
                status.innerText = "✅ 保存完了: " + fileName;
                status.style.color = "green";
            }};
            img.src = imgBase64;
        }}
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=100)

    if st.button("次の写真を撮る"):
        st.rerun()
