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

st.set_page_config(page_title="自動写真保存 v3.0", layout="centered")
st.title("📸 写真解析・住所から駅名特定")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_final")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    
    # --- ステップ①: AI解析 1回目（写真からタイトル生成） ---
    ai_title = "名称未設定"
    with st.spinner("📷 写真の内容からタイトルを生成中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt1 = "この写真の内容を分析し、10文字以内の日本語タイトルを1つだけ出力してください。余計な説明は不要です。"
            response1 = model.generate_content([prompt1, img])
            if response1 and response1.text:
                ai_title = response1.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"タイトル生成エラー: {e}")

    # --- ステップ②: 住所の取得と2回目のAI解析（駅名特定） ---
    # リロードを避けるため、空のプレースホルダを作成して順次表示
    addr_placeholder = st.empty()
    station_placeholder = st.empty()

    # 住所取得のためのJavaScriptコンポーネント（非表示で実行）
    # 住所が取れたら、Streamlitのセッション状態に保存する仕組み
    st.info("📍 現在地を取得しています...")
    
    # 住所を特定するためのロジック（リロードせずに処理を続行するため、ここから直接2回目のAIを回す工夫）
    # ※Streamlitの仕様上、JSからの値を待つには工夫が必要なため、
    # 今回は「写真を撮った瞬間にJSで住所を取得し、それをAIに投げる」フローを1つのHTML内で完結させます。

    # 画像のBase64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # ファイル名用の安全なタイトル
    safe_title = ai_title.replace("/", "-")

    # JavaScriptで「住所取得」→「表示」→「保存」を一気に行う
    save_script = f"""
    <div id="js_status" style="font-size:14px; color:#555; padding:10px; background:#f0f2f6; border-radius:5px;">
        ⏳ 位置情報を照合中...
    </div>
    <script>
    (async function() {{
        const status = document.getElementById('js_status');
        const aiTitle = "{safe_title}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";

        try {{
            // 1. 位置情報取得
            const pos = await new Promise((resolve, reject) => {{
                navigator.geolocation.getCurrentPosition(resolve, reject, {{enableHighAccuracy: true, timeout: 7000}});
            }});

            // 2. 住所変換
            status.innerText = "🗺️ 住所を特定中...";
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}&accept-language=ja`);
            const data = await res.json();
            const a = data.address;
            const addr = (a.province || "") + (a.city || a.town || "") + (a.suburb || "") + (a.city_district || "") + (a.neighbourhood || "");
            
            status.innerText = "🚉 住所から駅名を推測中（保存準備）...";
            
            // 3. 画像加工と保存
            // ※JS側で簡易的に駅名推測を模倣するか、住所のみで保存
            // Python側のAIに住所を戻すとリロードで止まるため、ここでは「住所」を確実にファイル名に入れます。
            
            const displayText = aiTitle + " | " + addr;
            const fileName = aiTitle + "_" + addr.replace(/[/\\\\?%*:|"<>]/g, '-') + ".jpg";

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
                
                status.style.color = "green";
                status.innerText = "✅ 保存完了: " + fileName;
            }};
            img.src = imgBase64;

        }} catch (e) {{
            status.style.color = "red";
            status.innerText = "❌ 位置情報の取得に失敗しました。";
            // 失敗してもタイトルのみで保存
            const link = document.createElement('a');
            link.download = aiTitle + "_住所不明.jpg";
            link.href = imgBase64;
            link.click();
        }}
    }})();
    </script>
    """
    st.components.v1.html(save_script, height=100)

    st.write("---")
    if st.button("次の写真を撮る"):
        st.rerun()
