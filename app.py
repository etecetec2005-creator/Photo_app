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
st.title("📸 写真内容解析 & 保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v25")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="位置情報を取得中...")

    # --- 2. JavaScriptで場所を先に特定 ---
    # コンポーネントを使用してJSから住所を受け取る
    # st.components.v1.htmlの中で住所を取得し、クエリパラメータ経由でPythonに戻す
    address_ready = st.query_params.get("addr")
    
    if not address_ready:
        st.info("📍 位置情報を照合しています...")
        get_addr_js = """
        <script>
        navigator.geolocation.getCurrentPosition(async (pos) => {
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&accept-language=ja`);
                const data = await res.json();
                const a = data.address;
                const finalAddr = (a.city || a.town || a.village || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
                
                // URLに住所をセットしてリロード（Python側に住所を渡す）
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
        st.stop() # 住所が取れるまで一旦停止

    # --- 3. 住所確定後、AI解析をスタート ---
    current_addr = address_ready
    ai_title = "名称未設定"
    
    with st.spinner(f"位置「{current_addr}」に基づきAI解析中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            # 住所情報をプロンプトに含める
            prompt = f"場所「{current_addr}」で撮影されたこの写真に、10文字以内の日本語タイトルを付けてください。回答はタイトルのみ。"
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                ai_title = response.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            if "429" in str(e):
                st.warning("⚠️ 利用制限中のためデフォルトタイトルで保存します。")
            else:
                st.warning(f"⚠️ 解析スキップ: {e}")

    # 4. 保存用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 5. JavaScriptで文字埋め込み ＋ JPG保存
    # 保存が終わったらURLパラメータをクリアするボタンを表示
    st.success(f"確定: {ai_title} @ {current_addr}")
    
    save_script = f"""
    <div id="status" style="font-size:12px; color:green; padding:10px;">✅ 保存処理を実行します...</div>
    <script>
    (function() {{
        const aiTitle = "{ai_title}";
        const addr = "{current_addr}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        const oW = {width};
        const oH = {height};

        const displayText = aiTitle + " _ " + addr;
        const fileName = aiTitle + "_" + addr.replace(/[/\\\\?%*:|"<>]/g, '-') + ".jpg";

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

    if st.button("次の写真を撮る"):
        st.query_params.clear()
        st.rerun()
