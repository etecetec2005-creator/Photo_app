import streamlit as st
import google.generativeai as genai
import requests
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

st.set_page_config(page_title="自動写真保存 v7.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# ==========================================
# ステップ①: 位置情報の取得（ユーザー操作を起点にする）
# ==========================================
lat = st.query_params.get("lat")
lon = st.query_params.get("lon")

# 緯度経度がまだ無い場合のみ、開始ボタンを表示
if not lat or not lon:
    st.warning("⚠️ 位置情報の許可が必要です。下のボタンを押してください。")
    
    # このボタンを押すことで、ブラウザが位置情報取得を許可します
    if st.button("📍 位置情報を取得してカメラを起動"):
        get_location_js = """
        <script>
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const url = new URL(window.location.href);
                url.searchParams.set("lat", pos.coords.latitude);
                url.searchParams.set("lon", pos.coords.longitude);
                window.location.href = url.href; // 強制リロード
            },
            (err) => {
                alert("位置情報の取得に失敗しました。設定を確認してください。");
                const url = new URL(window.location.href);
                url.searchParams.set("lat", "none");
                url.searchParams.set("lon", "none");
                window.location.href = url.href;
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
        </script>
        """
        st.components.v1.html(get_location_js, height=0)
    
    st.info("※ボタンを押しても反応がない場合は、ブラウザのアドレスバーにある「鍵マーク」から位置情報の許可を確認してください。")
    st.stop()

# ==========================================
# ステップ②: 住所変換 (Python側で実行 / 通信エラー回避)
# ==========================================
current_addr = "位置情報なし"
if lat != "none" and lon != "none":
    if "saved_addr" not in st.session_state:
        try:
            # Pythonから直接リクエストするので CORSエラー（Failed to fetch）は起きません
            headers = {'User-Agent': 'StreamlitApp/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=ja"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                a = data.get("address", {})
                # 住所の組み立て
                addr_str = (a.get("province", "") + a.get("city", a.get("town", "")) + 
                            a.get("suburb", "") + a.get("neighbourhood", ""))
                st.session_state.saved_addr = addr_str if addr_str else "住所特定不能"
            else:
                st.session_state.saved_addr = "住所取得失敗"
        except:
            st.session_state.saved_addr = "通信タイムアウト"
    current_addr = st.session_state.saved_addr

st.success(f"📍 現在地: {current_addr}")

# ==========================================
# ステップ③: カメラ & AI解析
# ==========================================
img_file = st.camera_input("写真を撮る", key="cam_v7")

if img_file:
    img = Image.open(img_file)
    
    # 1回目AI: タイトル生成
    ai_title = "名称未設定"
    with st.spinner("AI解析中 (1/2)..."):
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            response1 = model.generate_content(["10文字以内の日本語タイトルを1つだけ出力してください。", img])
            ai_title = response1.text.strip().replace("/", "-")
        except: pass

    # 2回目AI: 駅名特定
    near_station = "駅名不明"
    if "なし" not in current_addr:
        with st.spinner("AI解析中 (2/2)..."):
            try:
                # 住所テキストだけを渡して駅名を聞く
                prompt2 = f"住所「{current_addr}」の最寄り駅名を1つだけ答えてください。駅名以外は不要。"
                response2 = model.generate_content(prompt2)
                near_station = response2.text.strip().replace("/", "-")
            except: pass

    # ==========================================
    # ステップ④: 保存処理
    # ==========================================
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    final_text = f"{ai_title} | {current_addr} | {near_station}"
    final_file = f"{ai_title}_{current_addr}_{near_station}.jpg".replace(" ", "")

    st.info(f"保存名: {final_file}")

    save_js = f"""
    <script>
    (function() {{
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.onload = function() {{
            canvas.width = img.width; canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            const fontSize = Math.floor(img.height / 30);
            ctx.font = "bold " + fontSize + "px sans-serif";
            ctx.fillStyle = "rgba(0,0,0,0.6)";
            const tw = ctx.measureText("{final_text}").width;
            ctx.fillRect(10, 10, tw + 20, fontSize + 20);
            ctx.fillStyle = "white";
            ctx.fillText("{final_text}", 20, 20 + fontSize * 0.8);
            
            const link = document.createElement('a');
            link.download = "{final_file}";
            link.href = canvas.toDataURL('image/jpeg');
            link.click();
        }};
        img.src = "data:image/jpeg;base64,{img_str}";
    }})();
    </script>
    """
    st.components.v1.html(save_js, height=0)

    if st.button("リセット（次の場所へ）"):
        st.query_params.clear()
        st.rerun()
