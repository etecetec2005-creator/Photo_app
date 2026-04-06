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
st.title("📸 写真解析・駅名特定保存")

# 1. カメラ入力
img_file = st.camera_input("写真を撮る", key="camera_v26")

if img_file:
    # 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="解析準備中...")

    # --- 2. JavaScriptで位置情報を取得しURL経由でPythonに戻す ---
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
                // 市区町村〜町名までの住所を作成
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
        st.stop() # 住所が取れるまで停止

    # --- 3. 住所確定後、AI解析（2段階実行） ---
    current_addr = address_ready
    ai_title = "名称未設定"
    near_station = "駅名不明"
    
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    # 【解析 1回目：タイトル付与】
    with st.spinner(f"位置「{current_addr}」に基づきタイトルを生成中..."):
        try:
            prompt1 = f"場所「{current_addr}」付近で撮影されたこの写真に、10文字以内の日本語タイトルを付けてください。回答はタイトルのみ。"
            response1 = model.generate_content([prompt1, img])
            if response1 and response1.text:
                ai_title = response1.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"タイトル解析エラー: {e}")

    # 【解析 2回目：駅名特定】
    with st.spinner(f"周辺住所「{current_addr}」から最寄り駅を特定中..."):
        try:
            # 住所をヒントに画像から具体的な駅名（実在するもの）を推測させる
            prompt2 = f"指示：この写真と住所「{current_addr}」から、最も近い実在する駅名を1つ特定してください。回答は駅名のみ（例：新大阪駅）。駅が特定できない場合は『駅名不明』と回答してください。"
            response2 = model.generate_content([prompt2, img])
            if response2 and response2.text:
                near_station = response2.text.strip().replace("\n", "").replace("/", "-").replace(" ", "")
        except Exception as e:
            st.warning(f"駅名特定エラー: {e}")

    # 4. 保存用のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 5. ファイル名と表示用テキストの構築
    # 記号などの除去
    safe_addr = current_addr.replace("/", "-").replace("\\", "-")
    safe_station = near_station.replace("/", "-").replace("\\", "-")
    
    # 最終的なファイル名：タイトル_住所_駅名.jpg
    final_file_name = f"{ai_title}_{safe_addr}_{safe_station}.jpg"
    final_display_text = f"{ai_title} | {safe_addr} | {safe_station}"

    st.success(f"✅ 解析完了: {final_display_text}")
    
    # JavaScriptで文字埋め込み ＋ JPG保存
    save_script = f"""
    <div id="status" style="font-size:12px; color:green; padding:10px;">💾 ファイル「{final_file_name}」を保存しています...</div>
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
            
            // 背景ボックスを描画
            ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
            ctx.fillRect(20, 20, textWidth + (padding * 2), fontSize + (padding * 2));
            
            // テキストを描画
            ctx.fillStyle = "white";
            ctx.fillText(displayText, 20 + padding, 20 + padding);
            
            // ダウンロード実行
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
