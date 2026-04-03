import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io

# --- Gemini API 設定 ---
API_KEY = "AIzaSyAC6W0cwPmw3VrpxqXoiKZEv4CpIYUHME0"
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    with st.spinner("Geminiがタイトルを生成中..."):
        try:
            # モデル名の指定を最新版(-latest)に変更して試行
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            # 画像からタイトルを生成するプロンプト
            prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力し、説明は不要です。"
            
            # 安全にコンテンツを生成
            response = model.generate_content(
                contents=[prompt, img]
            )
            
            # レスポンスからテキストを抽出
            if response.text:
                title = response.text.strip()
                st.success(f"🏷️ タイトル: {title}")
            else:
                st.warning("タイトルを生成できませんでした。")
                
        except Exception as e:
            # エラーの詳細を表示
            st.error(f"Gemini解析エラー: {str(e)}")
            st.info("💡 404エラーが出る場合は、ライブラリのバージョンが古い可能性があります。 requirements.txt に google-generativeai>=0.5.0 を指定してください。")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 住所取得ロジック（都道府県抜き）
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const addr = data.address;
                let formattedAddress = "";
                
                if (addr.city) formattedAddress += addr.city;
                if (addr.suburb) formattedAddress += addr.suburb;
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) {
                    formattedAddress += addr.city_district;
                }
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                
                output.innerText = formattedAddress || "住所が見つかりませんでした";
            } catch (err) {
                output.innerText = "住所の特定に失敗しました。";
            }
        },
        (err) => {
            output.innerText = "エラー: 位置情報の許可が必要です。";
        },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
