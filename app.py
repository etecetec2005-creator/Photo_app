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

st.set_page_config(page_title="自動写真保存 v6.0", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# ==========================================
# ステップ①: カメラ起動「前」に位置情報を取得する
# ==========================================
# URLから緯度経度を取得
lat = st.query_params.get("lat")
lon = st.query_params.get("lon")

if not lat or not lon:
    st.info("📍 カメラを準備しています（位置情報を取得中...）")
    
    # ここでのみJavaScriptを実行し、緯度経度だけをURLにセットしてリロード
    get_location_js = """
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const url = new URL(window.location.href);
            url.searchParams.set("lat", pos.coords.latitude);
            url.searchParams.set("lon", pos.coords.longitude);
            window.location.replace(url.href); // 履歴に残さず遷移
        },
        (err) => {
            const url = new URL(window.location.href);
            url.searchParams.set("lat", "error");
            url.searchParams.set("lon", "error");
            window.location.replace(url.href);
        },
        { enableHighAccuracy: true, timeout: 8000 }
    );
    </script>
    """
    st.components.v1.html(get_location_js, height=0)
    st.stop() # 位置が取れるまでここでストップ

# ==========================================
# ステップ②: Pythonで住所に変換 (CORSエラー絶対回避)
# ==========================================
current_addr = "位置情報なし"

if lat != "error" and lon != "error":
    # 毎回APIを叩かないようセッションに保存
    if "saved_addr" not in st.session_state:
        try:
            # Pythonからリクエストを送るため、ブラウザのエラー(Failed to fetch)は起きません
            headers = {'User-Agent': 'StreamlitAutoPhotoApp/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=ja"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                a = data.get("address", {})
                addr_str = (a.get("province", "") + a.get("city", a.get("town", "")) + 
                            a.get("suburb", "") + a.get("neighbourhood", ""))
                st.session_state.saved_addr = addr_str if addr_str else "住所特定できず"
            else:
                st.session_state.saved_addr = "住所取得エラー"
        except Exception:
            st.session_state.saved_addr = "通信エラー"
            
    current_addr = st.session_state.saved_addr

st.success(f"📍 撮影場所: {current_addr}")

# ==========================================
# ステップ③: カメラ入力 ＆ AI解析 (一切リロードなし)
# ==========================================
img_file = st.camera_input("写真を撮る", key="main_camera")

if img_file:
    img = Image.open(img_file)
    width, height = img.size

    # 【AI 1回目】タイトルの生成
    ai_title = "名称未設定"
    with st.spinner("1/2: AIが写真を解析し、タイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
            response1 = model.generate_content([prompt1, img])
            if response1 and response1.text:
                ai_title = response1.text.strip().replace("\n", "").replace("/", "-")
        except Exception as e:
            st.warning(f"タイトル生成失敗: {e}")

    # 【AI 2回目】住所から駅名の特定
    near_station = "駅名不明"
    if "エラー" not in current_addr and "なし" not in current_addr:
        with st.spinner("2/2: AIが住所から最寄り駅を特定中..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                prompt2 = f"指示：住所「{current_addr}」に最も近い実在する駅名を1つだけ答えてください。駅名のみ出力してください（例：東京駅）。"
                # ここはテキストプロンプトのみでAIに聞く
                response2 = model.generate_content(prompt2)
                if response2 and response2.text:
                    near_station = response2.text.strip().replace("\n", "").replace("/", "-")
            except Exception as e:
                st.warning(f"駅名特定失敗: {e}")

    # ==========================================
    # ステップ④: JavaScriptで文字入れとダウンロード
    # ==========================================
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # ファイル名と印字テキストの生成
    safe_addr = current_addr.replace("/", "-")
    final_text = f"{ai_title} | {safe_addr} | {near_station}"
    final_file = f"{ai_title}_{safe_addr}_{near_station}.jpg"

    st.success(f"✅ すべて完了しました！")
    
    save_script = f"""
    <div style="text-align:center; margin-top:10px;">
        <b style="color:green; font-size:16px;">💾 画像を保存しました: {final_file}</b>
    </div>
    <script>
    (function() {{
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
            
            const txt = "{final_text}";
            const tw = ctx.measureText(txt).width;
            
            ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
            ctx.fillRect(20, 20, tw + fontSize, fontSize * 1.5);
            ctx.fillStyle = "white";
            ctx.fillText(txt, 20 + (fontSize/2), 20 + (fontSize/4));
            
            const link = document.createElement('a');
            link.download = "{final_file}";
            link.href = canvas.toDataURL('image/jpeg', 1.0);
            link.click();
        }};
        img.src = "data:image/jpeg;base64,{img_str}";
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=80)

    # 次の撮影用にリセット
    if st.button("次の場所で写真を撮る（リセット）"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
