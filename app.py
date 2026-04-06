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

st.set_page_config(page_title="自動写真保存 v2.9", layout="centered")
st.title("📸 写真解析 & 住所から駅名特定")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v29")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # --- ステップ①: AI解析 1回目（タイトル生成） ---
    if "ai_title" not in st.session_state:
        with st.spinner("AIがタイトルを生成中..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                prompt1 = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
                response1 = model.generate_content([prompt1, img])
                st.session_state.ai_title = response1.text.strip().replace("\n", "").replace("/", "-")
            except:
                st.session_state.ai_title = "名称未設定"

    # --- ステップ②: JavaScriptで住所を取得してリロード ---
    current_addr = st.query_params.get("addr")
    
    if not current_addr:
        st.info("📍 位置情報を取得して、駅名を特定します...")
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
        st.stop() 

    # --- ステップ③: AI解析 2回目（【重要】写真を見せず、住所のみから駅名を特定） ---
    ai_title = st.session_state.ai_title
    near_station = "駅名不明"
    
    with st.spinner(f"住所「{current_addr}」から最寄り駅を計算中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            # ここでは img（画像）を渡さず、テキストプロンプトのみで実行
            prompt2 = f"指示：住所「{current_addr}」に最も近い実在する駅名を1つだけ答えてください。余計な説明は一切不要です。駅名のみ出力してください（例：梅田駅）。"
            response2 = model.generate_content(prompt2) # テキストのみの解析
            if response2 and response2.text:
                near_station = response2.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"駅名特定エラー: {e}")

    # 4. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 5. ファイル名と文字入れ
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    final_file_name = f"{ai_title}_{safe_addr}_{near_station}.jpg"
    final_display_text = f"{ai_title} | {safe_addr} | {near_station}"

    st.success(f"✅ 解析完了: {final_display_text}")
    
    save_script = f"""
    <script>
    (function() {{
        const displayText = "{final_display_text}";
        const fileName = "{final_file_name}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        
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

    # 6. リセットボタン
    if st.button("次の写真を撮る"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
