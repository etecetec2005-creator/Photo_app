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

st.caption("※「住所取得エラー」が出る場合は、Wi-Fiをオフにしてモバイル通信で試すか、位置情報の許可を一度オフ→オンにしてください。")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # URLパラメータから住所を取得
    address_query = st.query_params.get("address", "")

    # --- Gemini 解析セクション ---
    with st.spinner("AIが解析中..."):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), 
                                available_models[0] if available_models else None)

            if target_model:
                model = genai.GenerativeModel(target_model)
                
                # 住所情報がある場合はプロンプトに含める
                location_context = f"現在の場所の住所は「{address_query}」付近です。" if address_query else "住所情報が取得できませんでした。"
                
                prompt = f"""
                {location_context}
                1. この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。
                2. 住所情報がある場合、そこから推測される「最寄り駅名」を特定してください。
                3. 出力形式は必ず「〇〇駅　[タイトル]」としてください（駅名が不明な場合は[タイトル]のみ）。
                4. 挨拶や説明は一切不要です。結果のみを出力してください。
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

    # 【改良版】住所取得スクリプト（エラー耐性を強化）
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    
    async function getAddress() {
        if (!navigator.geolocation) {
            output.innerText = "お使いのブラウザは位置情報に対応していません";
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                try {
                    // ユーザーエージェントを明示してNominatimの制限を回避しやすくする
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`, {
                        headers: { 'Accept-Language': 'ja', 'User-Agent': 'StreamlitPhotoApp' }
                    });
                    
                    if (!response.ok) throw new Error('Network response was not ok');
                    
                    const data = await response.json();
                    const addr = data.address;
                    let formattedAddress = "";
                    
                    // 都道府県を抜いた住所を構築
                    if (addr.city) formattedAddress += addr.city;
                    else if (addr.town) formattedAddress += addr.town;
                    else if (addr.village) formattedAddress += addr.village;
                    
                    if (addr.suburb) formattedAddress += addr.suburb;
                    if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                    if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                    if (addr.road) formattedAddress += addr.road;
                    
                    const finalAddr = formattedAddress || "住所詳細不明";
                    output.innerText = finalAddr;

                    // URLパラメータに保存（AI用）
                    const url = new URL(window.location);
                    if (url.searchParams.get('address') !== finalAddr) {
                        url.searchParams.set('address', finalAddr);
                        window.history.replaceState({}, '', url);
                    }
                } catch (err) { 
                    output.innerText = "住所検索サーバーが混み合っています。少し待ってから再度撮影してください。"; 
                }
            },
            (err) => { 
                output.innerText = "位置情報の取得が拒否されました。設定を確認してください。"; 
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    }
    getAddress();
    </script>
    """
    components.html(address_script, height=100)

    st.info("💡 保存するには、上の写真を長押ししてください。")
    
    if st.button("撮り直す"):
        st.query_params.clear()
        st.rerun()
