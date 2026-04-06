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
st.title("📸 写真解析・Gemini駅名特定")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v29_gemini_station")

if img_file:
    # URLパラメータから住所を確認
    current_addr = st.query_params.get("addr")

    # --- ステップ1: 住所がまだ無い場合、JSで取得してリロード（AI解析へ橋渡し） ---
    if current_addr is None:
        st.info("📍 位置情報を取得しています...")
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
                window.location.href = window.location.href + "?addr=住所取得エラー";
            }
        }, (err) => {
            window.location.href = window.location.href + "?addr=位置情報なし";
        }, { enableHighAccuracy: true });
        </script>
        """
        st.components.v1.html(get_addr_js, height=0)
        st.stop() # 住所が確定するまでここで停止

    # --- ステップ2: 住所確定後、Geminiに「タイトル」と「駅名」を出力させる ---
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption=f"取得住所: {current_addr}")

    ai_title = "名称未設定"
    near_station = "駅不明"

    with st.spinner("Gemini 2.5 Flash-Lite がタイトルと最寄り駅を解析中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # 住所をヒントとして与え、駅名を推論させる
            prompt = f"""
            指示:
            1. 以下の【撮影場所の住所】から判断して、最も近い「駅名」を1つ特定してください。
            2. この写真の内容にふさわしい短い日本語タイトル（10文字以内）を付けてください。
            
            【撮影場所の住所】: {current_addr}
            
            回答は必ず以下の形式のみで出力してください（余計な説明は不要です）:
            タイトル: [タイトル]
            駅名: [駅名]
            """
            
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                # AIの回答から「タイトル」と「駅名」を抽出
                lines = response.text.replace("*", "").split("\n")
                for line in lines:
                    if "タイトル" in line and ":" in line:
                        ai_title = line.split(":")[1].strip().replace("/", "-")
                    if "駅名" in line and ":" in line:
                        near_station = line.split(":")[1].strip().replace("/", "-")
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. JavaScriptで加工・保存（タイトル_住所_駅名.jpg）
    # Geminiが生成した ai_title と near_station を使用
    st.success(f"保存完了予定: {ai_title}_{current_addr}_{near_station}.jpg")
    
    save_script = f"""
    <script>
    (function() {{
        const aiTitle = "{ai_title}";
        const addr = "{current_addr}".replace(/[/\\\\?%*:|"<>]/g, '-');
        const station = "{near_station}".replace(/[/\\\\?%*:|"<>]/g, '-');
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
        }};
        img.src = imgBase64;
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=0)

    # 次の撮影のためのリセット
    if st.button("次の写真を撮る"):
        st.query_params.clear()
        st.rerun()
