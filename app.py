import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io
import os

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("APIキーが設定されていません。StreamlitのSecretsを確認してください。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# URLパラメータから住所を取得
addr_from_url = st.query_params.get("addr", "")

# 1. 写真撮影 (keyを明示して重複エラーを防止)
img_file = st.camera_input("写真を撮る", key="main_camera")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")
    st.write("---")

    # 2. 住所特定プロセス
    # まだ住所がURLにない場合のみ実行
    if not addr_from_url:
        st.subheader("📍 撮影場所を特定中...")
        
        # JavaScriptで位置取得→URL書き換え→リロード
        address_script = """
        <div id="status" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
            位置情報を取得しています...
        </div>
        <script>
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                try {
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`, {
                        headers: { 'Accept-Language': 'ja', 'User-Agent': 'StreamlitPhotoApp/3.0' }
                    });
                    const data = await response.json();
                    const addr = data.address;
                    let res = "";
                    if (addr.city || addr.town || addr.village) res += (addr.city || addr.town || addr.village);
                    if (addr.suburb) res += addr.suburb;
                    if (addr.city_district && !res.includes(addr.city_district)) res += addr.city_district;
                    if (addr.neighbourhood) res += addr.neighbourhood;
                    
                    const finalAddr = res || "住所特定失敗";

                    const url = new URL(window.location.href);
                    // addrパラメータがない場合のみ遷移を実行
                    if (!url.searchParams.has('addr')) {
                        url.searchParams.set('addr', finalAddr);
                        window.location.replace(url.href);
                    }
                } catch (err) { 
                    document.getElementById('status').innerText = "住所取得エラー。再試行してください。"; 
                }
            },
            (err) => { 
                document.getElementById('status').innerText = "位置情報を許可してください。"; 
            },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
        );
        </script>
        """
        components.html(address_script, height=100)
        st.info("住所を特定しています。完了すると自動でAI解析が始まります。")

    # 3. AI解析（住所がある場合）
    else:
        st.success(f"📍 撮影場所: {addr_from_url}")
        with st.spinner("AIが最寄り駅とタイトルを生成中..."):
            try:
                # 利用可能なモデルを取得
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
                model = genai.GenerativeModel(target_model)
                
                prompt = f"""
                現在の住所は「{addr_from_url}」です。
                1. この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。
                2. この住所から推測される「最寄り駅名」を特定してください。
                3. 出力形式は必ず「〇〇駅　[タイトル]」としてください。
                4. 結果のみを1行で出力し、挨拶や解説は省いてください。
                """
                
                response = model.generate_content([prompt, img])
                if response.text:
                    st.success(f"🏷️ {response.text.strip()}")
                else:
                    st.warning("解析結果が空でした。")
            except Exception as e:
                st.error(f"解析エラー: {str(e)}")

    st.write("---")
    # 撮り直しボタンにもkeyを付けて重複を避ける
    if st.button("撮り直す", key="reset_button"):
        st.query_params.clear()
        st.rerun()
