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

st.set_page_config(page_title="自動写真保存 v3.5", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# --- ステップ①: 住所情報のチェック ---
# query_paramsから確実に住所を取得
params = st.query_params
current_addr = params.get("addr")

# 住所がない場合は、住所取得用のJSだけを表示して停止する
if not current_addr:
    st.info("📍 位置情報を特定しています。ブラウザの許可ダイアログが出たら「許可」を押してください...")
    
    get_addr_js = """
    <script>
    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&accept-language=ja`);
            const data = await res.json();
            const a = data.address;
            const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
            
            // 住所をURLにセットしてリロード
            const url = new URL(window.location.href);
            url.searchParams.set("addr", finalAddr || "住所不明");
            window.location.href = url.href; 
        } catch (e) {
            window.location.href = window.location.href + "?addr=住所取得エラー";
        }
    }, (err) => {
        window.location.href = window.location.href + "?addr=位置情報取得失敗";
    }, { enableHighAccuracy: true, timeout: 10000 });
    </script>
    """
    st.components.v1.html(get_addr_js, height=0)
    st.stop() # ここで止めることで、住所がないままカメラが出るのを防ぐ

# --- ステップ②: 住所が確定している場合のみ、ここから下が実行される ---
st.success(f"📍 現在地特定済み: {current_addr}")

img_file = st.camera_input("写真を撮る", key="camera_v35_final")

if img_file:
    img = Image.open(img_file)
    width, height = img.size 
    
    ai_title = "名称未設定"
    near_station = "駅不明"

    with st.spinner("Geminiが「タイトル」と「最寄り駅」を厳密に特定中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # JSON形式での出力を厳格に指示
            prompt = f"""
            指示:
            1. 以下の【撮影地の住所】に最も近い「実在する駅名」を推測してください。
            2. この写真の内容を表す10文字以内の「日本語タイトル」を付けてください。
            
            【撮影地の住所】: {current_addr}
            
            回答は必ず以下のJSON形式のみで出力してください。
            {{
                "title": "ここにタイトル",
                "station": "ここに駅名"
            }}
            """
            
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                res_text = response.text.strip()
                # マークダウン除去
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(res_text)
                ai_title = data.get("title", "名称未設定")
                near_station = data.get("station", "駅不明")
                
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # ファイル名と表示用テキストの構築
    safe_title = ai_title.replace("/", "-").replace("\\", "-")
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    
    final_file_name = f"{safe_title}_{safe_addr}_{safe_station}.jpg"
    final_display_text = f"{safe_title} | {safe_addr} | {safe_station}"

    st.info(f"保存準備完了: {final_file_name}")
    
    # 保存と文字入れの実行
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
    if st.button("リセット（別の場所で撮る）"):
        st.query_params.clear()
        st.rerun()
