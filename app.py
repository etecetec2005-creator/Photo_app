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

st.caption("※カメラが起動しない場合は、ブラウザの許可を確認してください。")

# 住所情報をセッション状態で管理
if "detected_address" not in st.session_state:
    st.session_state.detected_address = ""

# カメラ入力
img_file = st.camera_input("1. 写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    st.write("---")
    st.subheader("📍 2. 撮影場所を特定中...")

    # 住所取得ロジック（取得したらSession Stateへ渡す）
    address_script = f"""
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    navigator.geolocation.getCurrentPosition(
        async (pos) => {{
            try {{
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{pos.coords.latitude}}&lon=${{pos.coords.longitude}}`, {{
                    headers: {{ 'Accept-Language': 'ja' }}
                }});
                const data = await response.json();
                const addr = data.address;
                let res = "";
                if (addr.city || addr.town || addr.village) res += (addr.city || addr.town || addr.village);
                if (addr.suburb) res += addr.suburb;
                if (addr.city_district && !res.includes(addr.city_district)) res += addr.city_district;
                if (addr.neighbourhood) res += addr.neighbourhood;
                
                const finalAddr = res || "住所特定失敗";
                output.innerText = finalAddr;

                // StreamlitのURLパラメータにセットして自動リロードさせる
                const url = new URL(window.location);
                if (url.searchParams.get('addr') !== finalAddr) {{
                    url.searchParams.set('addr', finalAddr);
                    window.location.href = url.href;
                }}
            }} catch (err) {{ output.innerText = "住所取得エラー"; }}
        }},
        (err) => {{ output.innerText = "位置情報を許可してください"; }},
        {{ enableHighAccuracy: true }}
    );
    </script>
    """
    components.html(address_script, height=80)

    # URLパラメータから住所を取得
    addr_from_url = st.query_params.get("addr", "")

    # --- 3. AIに駅名とタイトル付与を指示 ---
    if addr_from_url:
        with st.spinner("AIが最寄り駅とタイトルを生成中..."):
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                    available_models[0] if available_models else None)

                if target_model:
                    model = genai.GenerativeModel(target_model)
                    
                    # 住所情報をAIに伝える
                    prompt = f"""
                    現在の住所は「{addr_from_url}」です。
                    1. この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。
                    2. この住所から推測される「最寄り駅名」を特定してください。
                    3. 出力は必ず「〇〇駅　[タイトル]」という形式で、結果のみを1行で出力してください。
                    """
                    
                    response = model.generate_content([prompt, img])
                    
                    if response.text:
                        # --- 4. 駅名とタイトル表示 ---
                        st.success(f"🏷️ {response.text.strip()}")
                    else:
                        st.warning("解析に失敗しました。")
                else:
                    st.error("モデルが見つかりません。")
            except Exception as e:
                st.error(f"解析エラー: {str(e)}")
    else:
        st.info("住所の特定を待っています...（特定後に自動でAI解析が始まります）")

    st.write("---")
    st.info("💡 保存するには、上の写真を長押ししてください。")
    
    if st.button("撮り直す"):
        st.query_params.clear()
        st.rerun()
