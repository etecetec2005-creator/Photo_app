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
st.title("📸 写真解析・駅名特定保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v30_strict")

if img_file:
    # URLパラメータから住所を取得
    current_addr = st.query_params.get("addr")

    # --- ステップ①: 住所がまだ無い場合、JavaScriptで取得して「強制リロード」 ---
    if not current_addr:
        st.info("📍 位置情報を取得しています... しばらくお待ちください")
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
                window.location.href = url.href; // ここでリロードしてPythonを再実行
            } catch (e) {
                window.location.href = window.location.href + "?addr=住所取得エラー";
            }
        }, (err) => {
            window.location.href = window.location.href + "?addr=位置情報なし";
        }, { enableHighAccuracy: true });
        </script>
        """
        st.components.v1.html(get_addr_js, height=0)
        st.stop() # 住所が確定するまで、これ以降の「AI解析」へ絶対に進ませない

    # --- ステップ②: 住所が確定（URLに存在）している時だけ実行されるAI解析 ---
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption=f"📍 取得住所: {current_addr}")

    ai_title = "名称未設定"
    near_station = "駅不明"

    with st.spinner("Geminiが「タイトル」と「最寄り駅」を特定中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # Geminiに住所を渡し、駅名を答えさせる
            prompt = f"""
            指示:
            1. 以下の【住所】の近くにある「駅名」を1つ特定してください。
            2. この写真の内容に合う10文字以内の「日本語タイトル」を付けてください。
            
            【住所】: {current_addr}
            
            回答は必ず以下の形式を守ってください。
            タイトル: [タイトル]
            駅名: [駅名]
            """
            
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                res_text = response.text.replace("*", "")
                for line in res_text.strip().split("\n"):
                    if "タイトル" in line and ":" in line:
                        ai_title = line.split(":")[1].strip()
                    if "駅名" in line and ":" in line:
                        near_station = line.split(":")[1].strip()
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. JavaScriptで加工・保存（ファイル名: タイトル_住所_駅名.jpg）
    st.success(f"確定: {ai_title}_{current_addr}_{near_station}.jpg")
    
    # 禁止文字を掃除
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    
    save_script = f"""
    <script>
    (function() {{
        const aiTitle = "{ai_title}";
        const addr = "{safe_addr}";
        const station = "{safe_station}";
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
