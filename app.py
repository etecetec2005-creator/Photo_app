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

st.set_page_config(page_title="自動写真保存 v2.5", layout="centered")
st.title("📸 写真解析・駅名確実保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v27_station_fix")

if img_file:
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="位置情報と駅名を照合中...")

    # --- 2. JavaScriptで住所と「最寄り駅」を先に特定 ---
    current_addr = st.query_params.get("addr")
    near_station = st.query_params.get("st")
    
    if not current_addr or not near_station:
        st.info("📍 最寄り駅を検索しています...")
        get_info_js = """
        <script>
        navigator.geolocation.getCurrentPosition(async (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            try {
                // 住所取得 (Nominatim)
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&accept-language=ja`);
                const data = await res.json();
                const a = data.address;
                const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
                
                // 最寄り駅取得 (Overpass API - 半径1km以内の駅を検索)
                let stationName = "駅不明";
                try {
                    const query = `[out:json];node(around:1000,${lat},${lon})[railway=station];out;`;
                    const sRes = await fetch("https://overpass-api.de/api/interpreter?data=" + encodeURIComponent(query));
                    const sData = await sRes.json();
                    if (sData.elements && sData.elements.length > 0) {
                        stationName = sData.elements[0].tags.name || "駅名なし";
                    }
                } catch(e) {}

                const url = new URL(window.location.href);
                url.searchParams.set("addr", finalAddr || "住所不明");
                url.searchParams.set("st", stationName);
                window.location.href = url.href;
            } catch (e) {
                window.location.href = window.location.href + "?addr=取得エラー&st=駅不明";
            }
        }, (err) => {
            window.location.href = window.location.href + "?addr=位置情報なし&st=不明";
        }, { enableHighAccuracy: true });
        </script>
        """
        st.components.v1.html(get_info_js, height=0)
        st.stop()

    # --- 3. 確定した情報を元にAIで「タイトル」だけを生成 ---
    ai_title = "名称未設定"
    with st.spinner("AIがタイトルを付けています..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            # 住所と駅名をAIに教えて、最適なタイトルを考えさせる
            prompt = f"場所「{current_addr}」、最寄り駅「{near_station}」で撮影されたこの写真に、10文字以内の日本語タイトルを1つ付けて。回答はタイトルのみ。"
            response = model.generate_content([prompt, img])
            if response and response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-")
        except:
            pass

    # 4. 保存用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 5. JavaScriptで加工・保存（タイトル_住所_駅名.jpg）
    st.success(f"確定: {ai_title} / {current_addr} / {near_station}")
    
    save_script = f"""
    <div id="status" style="font-size:12px; color:green; padding:10px;">✅ 保存実行中...</div>
    <script>
    (function() {{
        const aiTitle = "{ai_title}";
        const addr = "{current_addr}".replace(/[/\\\\?%*:|"<>]/g, '-');
        const station = "{near_station}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        const oW = {width};
        const oH = {height};

        const displayText = aiTitle + " | " + addr + " | " + station;
        const fileName = aiTitle + "_" + addr + "_" + station + ".jpg";

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
            document.getElementById('status').innerText = "✅ 保存完了: " + fileName;
        }};
        img.src = imgBase64;
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=50)

    if st.button("次の写真を撮る"):
        st.query_params.clear()
        st.rerun()
