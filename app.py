import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import base64
import json

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="自動写真保存 v3", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# --- ステップ①: カメラを出す前に、まず住所を確定させる ---
current_addr = st.query_params.get("addr")

if not current_addr:
    st.info("📍 現在地の住所を取得しています。許可を求められたら「許可」してください...")
    get_addr_js = """
    <script>
    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&accept-language=ja`);
            const data = await res.json();
            const a = data.address;
            const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
            
            const url = new URL(window.location.href);
            url.searchParams.set("addr", finalAddr || "住所不明");
            window.location.href = url.href; 
        } catch (e) {
            const url = new URL(window.location.href);
            url.searchParams.set("addr", "住所取得エラー");
            window.location.href = url.href;
        }
    }, (err) => {
        const url = new URL(window.location.href);
        url.searchParams.set("addr", "位置情報なし");
        window.location.href = url.href;
    }, { enableHighAccuracy: true });
    </script>
    """
    st.components.v1.html(get_addr_js, height=0)
    st.stop() # 住所がURLに入るまで、ここから下は絶対に実行させない

# --- ステップ②: 住所が確定してから、初めてカメラを表示する ---
st.success(f"📍 現在地: {current_addr}")

# ユーザーは必ず「住所確定後」に写真を撮ることになる
img_file = st.camera_input("写真を撮る", key="camera_v32_json")

if img_file:
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="AIがタイトルと最寄り駅を解析中...")

    ai_title = "名称未設定"
    near_station = "駅不明"

    with st.spinner("Gemini 2.5 Flash-Lite が解析中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # JSON形式での出力をAIに強制する
            prompt = f"""
            あなたは写真と住所から情報を抽出するAIです。
            以下の【撮影地の住所】に最も近い「実在する駅名」を推測し、写真の内容を表す「10文字以内の日本語タイトル」をつけてください。
            
            【撮影地の住所】: {current_addr}
            
            出力は必ず以下のJSON形式のみで行い、マークダウン(```json)などの装飾は一切含めないでください。
            {{
                "title": "ここにタイトル",
                "station": "ここに駅名"
            }}
            """
            
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                res_text = response.text.strip()
                # AIが余計なマークダウンを付けた場合の除去処理
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                
                # JSONとしてパースして確実に取り出す
                data = json.loads(res_text)
                ai_title = data.get("title", "名称未設定")
                near_station = data.get("station", "駅不明")
                
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. Python側でファイル名を完全に固定
    safe_title = ai_title.replace("/", "-").replace("\\", "-")
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    
    final_file_name = f"{safe_title}_{safe_addr}_{safe_station}.jpg"
    final_display_text = f"{safe_title} | {safe_addr} | {safe_station}"

    st.success(f"✅ 保存完了: {final_file_name}")
    
    save_script = f"""
    <script>
    (function() {{
        const fileName = "{final_file_name}";
        const displayText = "{final_display_text}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        const oW = {width};
        const oH = {height};

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
        }};
        img.src = imgBase64;
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=0)

    # 別の場所で再試行するためのリセットボタン
    st.write("---")
    if st.button("リセットして別の場所で撮る"):
        st.query_params.clear()
        st.rerun()
