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

st.set_page_config(page_title="自動写真保存 v4.6", layout="centered")
st.title("📸 写真解析・駅名特定保存")

# --- セッション状態の初期化 ---
if "image_data" not in st.session_state:
    st.session_state.image_data = None
if "ai_title" not in st.session_state:
    st.session_state.ai_title = None

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v46")

# 新しく写真が撮られたらセッションを更新
if img_file:
    st.session_state.image_data = img_file.getvalue()
    # 1回目のAI解析（タイトル生成）
    with st.spinner("AIがタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            temp_img = Image.open(io.BytesIO(st.session_state.image_data))
            prompt1 = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。"
            response = model.generate_content([prompt1, temp_img])
            st.session_state.ai_title = response.text.strip().replace("\n", "").replace("/", "-")
        except:
            st.session_state.ai_title = "名称未設定"

# 2. 写真がある場合、住所取得プロセスへ
if st.session_state.image_data:
    current_addr = st.query_params.get("addr")

    # 住所がまだURLにない場合、JavaScriptで取得してリロード
    if not current_addr:
        st.info("📍 位置情報を照合中... (10秒以上かかる場合は自動でスキップします)")
        
        # タイムアウト付き位置情報取得JS
        get_addr_js = """
        <script>
        const timeout = setTimeout(() => {
            window.location.href = window.location.href + "?addr=位置情報タイムアウト";
        }, 10000); // 10秒で強制終了

        navigator.geolocation.getCurrentPosition(async (pos) => {
            clearTimeout(timeout);
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&accept-language=ja`);
                const data = await res.json();
                const a = data.address;
                const finalAddr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.neighbourhood || "");
                
                const url = new URL(window.location.href);
                url.searchParams.set("addr", finalAddr || "住所不明");
                window.location.href = url.href; 
            } catch (e) {
                window.location.href = window.location.href + "?addr=住所取得エラー";
            }
        }, (err) => {
            clearTimeout(timeout);
            window.location.href = window.location.href + "?addr=位置情報なし";
        }, { enableHighAccuracy: true, timeout: 8000 });
        </script>
        """
        st.components.v1.html(get_addr_js, height=0)
        st.stop()

    # --- 3. 住所確定後の処理（2回目のAI解析：駅名特定） ---
    img = Image.open(io.BytesIO(st.session_state.image_data))
    ai_title = st.session_state.ai_title
    near_station = "駅名不明"

    # 住所が取れている場合のみ、AIに駅名を聞く
    if "住所" not in current_addr and "位置情報" not in current_addr:
        with st.spinner(f"住所「{current_addr}」から最寄り駅を特定中..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                prompt2 = f"指示：住所「{current_addr}」に最も近い実在する駅名を1つだけ答えてください。駅名のみ出力してください（例：東京駅）。"
                response2 = model.generate_content(prompt2)
                if response2 and response2.text:
                    near_station = response2.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
            except:
                pass
    else:
        near_station = "特定不可"

    # 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 表示と保存
    final_text = f"{ai_title} | {current_addr} | {near_station}"
    # ファイル名から禁止文字を排除
    safe_addr = current_addr.replace("/", "-").replace("?", "")
    final_file = f"{ai_title}_{safe_addr}_{near_station}.jpg"
    
    st.success(f"✅ 解析完了: {final_text}")

    save_script = f"""
    <script>
    (function() {{
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.onload = function() {{
            canvas.width = {img.width};
            canvas.height = {img.height};
            ctx.drawImage(img, 0, 0, {img.width}, {img.height});
            const fontSize = Math.floor({img.height} / 30);
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
    st.components.v1.html(save_script, height=0)

    if st.button("次の写真を撮る"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
