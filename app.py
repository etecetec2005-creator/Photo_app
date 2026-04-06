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

st.set_page_config(page_title="自動写真保存 v4.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# --- ステップ①: 住所取得プロセス ---
current_addr = st.query_params.get("addr")

if not current_addr:
    st.info("📍 位置情報を特定しています。ブラウザの『位置情報の使用』を許可してください...")
    
    # 取得に失敗した際や、時間がかかりすぎた場合のレスキューボタン
    if st.button("取得が進まない場合はここをクリック"):
        st.query_params.clear()
        st.rerun()

    get_addr_js = """
    <script>
    const options = {
        enableHighAccuracy: true,
        timeout: 10000,   // 10秒待つ
        maximumAge: 0
    };

    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&accept-language=ja`);
            const data = await res.json();
            const a = data.address;
            const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
            
            const url = new URL(window.location.href);
            url.searchParams.set("addr", finalAddr || "住所不明");
            window.location.replace(url.href); // 履歴に残さず置換
        } catch (e) {
            window.location.replace(window.location.href.split('?')[0] + "?addr=住所取得エラー");
        }
    }, (err) => {
        let msg = "位置情報なし";
        if(err.code === 1) msg = "位置情報へのアクセスが拒否されました";
        window.location.replace(window.location.href.split('?')[0] + "?addr=" + msg);
    }, options);
    </script>
    """
    st.components.v1.html(get_addr_js, height=0)
    st.stop() 

# --- ステップ②: 住所確定後のメイン画面 ---
st.success(f"📍 現在地: {current_addr}")

# 住所にエラーが含まれる場合の警告
if "拒否" in current_addr or "エラー" in current_addr:
    st.warning("位置情報が正常に取得できていません。ブラウザの設定で位置情報を「許可」してから、下のボタンでやり直してください。")
    if st.button("もう一度位置情報を取得する"):
        st.query_params.clear()
        st.rerun()

img_file = st.camera_input("写真を撮る", key="camera_v40_final")

if img_file:
    img = Image.open(img_file)
    width, height = img.size 

    ai_title = "名称未設定"
    near_station = "駅不明"

    with st.spinner("Geminiが「タイトル」と「最寄り駅」を特定中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt = f"""
            以下の【住所】の近くにある「実在する駅名」を1つ特定し、写真に合う10文字以内の「日本語タイトル」を付けてください。
            
            【住所】: {current_addr}
            
            回答形式:
            タイトル: [ここにタイトル]
            駅名: [ここに駅名]
            """
            response = model.generate_content([prompt, img])
            if response and response.text:
                res_text = response.text.replace("*", "").replace("：", ":")
                for line in res_text.strip().split("\n"):
                    if "タイトル" in line and ":" in line:
                        ai_title = line.split(":", 1)[1].strip()
                    if "駅名" in line and ":" in line:
                        near_station = line.split(":", 1)[1].strip()
        except Exception as e:
            st.warning(f"AI解析エラー: {e}")

    # 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # ファイル名作成
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    safe_title = ai_title.replace("/", "-").replace("\\", "-")
    final_file_name = f"{safe_title}_{safe_addr}_{safe_station}.jpg"
    final_display_text = f"{safe_title} | {safe_addr} | {safe_station}"

    st.success(f"✅ 保存完了: {final_file_name}")
    
    # JavaScriptで加工・保存
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

    if st.button("別の場所で撮影する（リセット）"):
        st.query_params.clear()
        st.rerun()
