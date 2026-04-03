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

st.caption("※「住所取得エラー」が続く場合は、一度ページを再読み込みしてください。")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # URLパラメータまたはセッションから住所を取得
    address_query = st.query_params.get("address", "")

    # --- Gemini 解析セクション ---
    with st.spinner("AIが解析中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                location_context = f"現在の場所の住所は「{address_query}」付近です。" if address_query else "住所情報が取得できませんでした。"
                
                prompt = f"""
                {location_context}
                1. この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。
                2. 住所情報から推測される「最寄り駅名」を特定してください。
                3. 出力形式は必ず「〇〇駅　[タイトル]」としてください。
                4. 挨拶や説明は一切不要です。
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success(f"🏷️ {response.text.strip()}")
                else:
                    st.warning("解析結果を取得できませんでした。")
            else:
                st.error("利用可能なAIモデルが見つかりませんでした。")
                
        except Exception as e:
            st.error("解析エラーが発生しました。")
            st.code(f"Detail: {str(e)}")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 【安定化版】キャッシュ機能付き住所取得スクリプト
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');

    async function fetchWithRetry(url, retries = 3, backoff = 1000) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(url, {
                    headers: { 'Accept-Language': 'ja', 'User-Agent': 'MyPhotoApp/1.0' }
                });
                if (response.ok) return await response.json();
                if (response.status === 429) await new Promise(r => setTimeout(r, backoff * (i + 1)));
            } catch (err) {
                if (i === retries - 1) throw err;
            }
        }
    }

    async function getAddress() {
        // キャッシュチェック（5分以内なら再利用）
        const cached = localStorage.getItem('last_addr');
        const cachedTime = localStorage.getItem('last_addr_time');
        if (cached && cachedTime && (Date.now() - cachedTime < 300000)) {
            output.innerText = cached;
            updateURL(cached);
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const { latitude: lat, longitude: lon } = pos.coords;
                try {
                    const data = await fetchWithRetry(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18`);
                    const addr = data.address;
                    let res = "";
                    if (addr.city || addr.town || addr.village) res += (addr.city || addr.town || addr.village);
                    if (addr.suburb) res += addr.suburb;
                    if (addr.city_district && !res.includes(addr.city_district)) res += addr.city_district;
                    if (addr.neighbourhood) res += addr.neighbourhood;
                    
                    const finalAddr = res || "住所不明";
                    output.innerText = finalAddr;
                    
                    // キャッシュ保存
                    localStorage.setItem('last_addr', finalAddr);
                    localStorage.setItem('last_addr_time', Date.now());
                    updateURL(finalAddr);
                } catch (err) { 
                    output.innerText = "サーバー制限中。少し時間を置いてください。"; 
                }
            },
            (err) => { output.innerText = "位置情報を許可してください。"; },
            { enableHighAccuracy: true, timeout: 5000 }
        );
    }

    function updateURL(addr) {
        const url = new URL(window.location);
        if (url.searchParams.get('address') !== addr) {
            url.searchParams.set('address', addr);
            window.history.replaceState({}, '', url);
        }
    }
    
    getAddress();
    </script>
    """
    components.html(address_script, height=100)

    st.info("💡 保存するには、上の写真を長押ししてください。")
    
    if st.button("撮り直す"):
        st.query_params.clear()
        st.rerun()
