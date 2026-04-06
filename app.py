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
img_file = st.camera_input("写真を撮る", key="camera_v26_final")

if img_file:
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="位置情報を取得中...")

    # --- 2. JavaScriptで住所を先に特定 ---
    current_addr = st.query_params.get("addr")
    
    if not current_addr:
        st.info("📍 現在地を照合しています...")
        get_addr_js = """
        <script>
        navigator.geolocation.getCurrentPosition(async (pos) => {
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&accept-language=ja`);
                const data = await res.json();
                const a = data.address;
                // 住所を詳細に組み立て
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
        st.stop()

    # --- 3. AI解析（タイトル ＋ 駅名の抽出を強化） ---
    ai_title = "名称未設定"
    near_station = "駅不明"
    
    with st.spinner("AIがタイトルと最寄り駅を特定しています..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            prompt = f"""
            指示:
            1. 以下の【住所】のすぐ近くにある「駅名」を1つだけ答えてください（例: 新大阪駅）。
            2. この写真の内容にふさわしい短い日本語タイトル（10文字以内）を付けてください。
            
            【住所】: {current_addr}
            
            回答は必ず以下の2行の形式のみで出力してください。
            タイトル: [ここにタイトル]
            駅名: [ここに駅名]
            """
            
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                text = response.text.replace("*", "").replace("　", "") # 記号などを掃除
                for line in text.strip().split("\n"):
                    if "タイトル" in line and ":" in line:
                        ai_title = line.split(":")[1].strip().replace("/", "-")
                    if "駅名" in line and ":" in line:
                        near_station = line.split(":")[1].strip().replace("/", "-")
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 4. 保存用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 5. JavaScriptで加工・保存（ファイル名: タイトル_住所_駅名.jpg）
    st.success(f"確定: {ai_title} / {current_addr} / {near_station}")
    
    # URLパラメータの住所には「/」が含まれる場合があるため念入りに置換
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    
    save_script = f"""
    <div id="status" style="font-size:12px; color:green; padding:10px;">✅ 保存処理中...</div>
    <script>
    (function() {{
        const aiTitle = "{ai_title}";
        const addr = "{safe_addr}";
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
