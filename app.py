import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import os

# --- セキュリティ設定（Secretsから取得） ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("APIキーが設定されていません。Secretsを確認してください。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

st.caption("※カメラが起動しない場合は、ブラウザの「鍵マーク」からカメラ許可を確認してください。")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    ai_title_value = "" # JavaScriptに渡すための変数
    with st.spinner("AIが解析中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力してください。"
                response = model.generate_content([prompt, img])
                
                if response.text:
                    ai_title_value = response.text.strip().replace('"', '').replace("'", "") # 引用符を除去
                    st.success(f"🏷️ タイトル: {ai_title_value}")
                else:
                    st.warning("タイトルを生成できませんでした。")
            else:
                st.error("利用可能なAIモデルが見つかりませんでした。")
                
        except Exception as e:
            st.error("解析エラーが発生しました。")
            st.code(f"Detail: {str(e)}")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 1. 画像データをJavaScriptで扱える形式（Base64）に変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    import base64
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 2. 住所取得 + 自動命名ダウンロードボタン
    address_script = f"""
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px; margin-bottom:10px;">
        位置情報を取得中...
    </div>
    <button id="dl-btn" style="display:none; width:100%; padding:10px; background-color:#ff4b4b; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">
        📥 この名前で保存する
    </button>

    <script>
    const output = document.getElementById('address-out');
    const dlBtn = document.getElementById('dl-btn');
    const aiTitle = "{ai_title_value}" || "名称未設定";
    const imgData = "data:image/jpeg;base64,{img_str}";

    navigator.geolocation.getCurrentPosition(
        async (pos) => {{
            try {{
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                    headers: {{ 'Accept-Language': 'ja' }}
                }});
                const data = await response.json();
                const addr = data.address;
                let formattedAddress = "";
                if (addr.city) formattedAddress += addr.city;
                if (addr.suburb) formattedAddress += addr.suburb;
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                
                const finalAddr = formattedAddress || "住所特定失敗";
                output.innerText = finalAddr;

                // ダウンロードボタンを表示してクリック時の動作を設定
                dlBtn.style.display = "block";
                dlBtn.innerText = "📥 「" + finalAddr + "_" + aiTitle + ".jpg」を保存";
                
                dlBtn.onclick = () => {{
                    const link = document.createElement('a');
                    link.href = imgData;
                    link.download = finalAddr + "_" + aiTitle + ".jpg";
                    link.click();
                }};

            }} catch (err) {{ output.innerText = "住所取得エラー"; }}
        }},
        (err) => {{ output.innerText = "位置情報を許可してください"; }},
        {{ enableHighAccuracy: true }}
    );
    </script>
    """
    components.html(address_script, height=150)

    st.info("💡 下の赤いボタンを押すと、AIタイトルと住所が付いた名前で保存されます。")
    
    if st.button("撮り直す"):
        st.rerun()
