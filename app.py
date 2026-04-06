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

st.set_page_config(page_title="自動写真保存 v2.6", layout="centered")
st.title("📸 写真解析 & 保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v26")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="プロセス実行中...")

    # --- ステップ①: 1回目のAI解析（タイトル生成） ---
    ai_title = "名称未設定"
    if "ai_title" not in st.session_state:
        with st.spinner("タイトルを生成中..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                prompt = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
                response = model.generate_content([prompt, img])
                if response and response.text:
                    ai_title = response.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
                    st.session_state.ai_title = ai_title
            except Exception as e:
                st.warning(f"タイトル解析失敗: {e}")
    else:
        ai_title = st.session_state.ai_title

    # --- ステップ②: JavaScriptで住所を取得してURL経由でPythonに戻す ---
    current_addr = st.query_params.get("addr")
    
    if not current_addr:
        st.info("📍 位置情報を照合しています...")
        get_addr_js = """
        <script>
        navigator.geolocation.getCurrentPosition(async (pos) => {
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&accept-language=ja`);
                const data = await res.json();
                const a = data.address;
                const finalAddr = (a.city || a.town || a.village || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
                
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

    # --- ステップ③: 2回目のAI解析（確定した住所に基づき駅名を特定） ---
    near_station = "駅名不明"
    with st.spinner(f"住所「{current_addr}」から最寄り駅を特定中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            # 住所情報を渡して、写真と照らし合わせる
            prompt2 = f"この写真と住所「{current_addr}」を照合し、最も近い実在する駅名を1つだけ出力してください。回答は駅名のみ。駅が特定できない場合は『駅名不明』と答えてください。"
            response2 = model.generate_content([prompt2, img])
            if response2 and response2.text:
                near_station = response2.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"駅名特定失敗: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. ファイル名と表示用テキストの構築
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    
    # ファイル名: タイトル_住所_駅名.jpg
    final_file_name = f"{ai_title}_{safe_addr}_{safe_station}.jpg"
    final_display_text = f"{ai_title} | {safe_addr} | {safe_station}"

    st.success(f"解析完了: {final_display_text}")
    
    # 5. JavaScriptで文字埋め込み ＋ JPG保存
    save_script = f"""
    <div id="status" style="font-size:12px; color:green; padding:10px;">✅ 保存処理を実行中: {final_file_name}</div>
    <script>
    (function() {{
        const displayText = "{final_display_text}";
        const fileName = "{final_file_name}";
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
    st.components.v1.html(save_script, height=50)

    # 次の撮影のためのリセット
    if st.button("次の写真を撮る"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
