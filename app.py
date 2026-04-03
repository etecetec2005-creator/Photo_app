import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
from PIL import Image
import io

# --- JAPAN AI 設定 ---
API_KEY = "0a36d931-68fc-495d-a017-da4b8757d8f1"
API_URL = "https://api.japan-ai.co.jp/chat/v2"
API_MODEL_TITLE = "gpt-4o-mini"
# 今回は「今撮った写真」を優先するため、artifactIdsはリクエスト時に制御します

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- JAPAN AI 解析セクション ---
    with st.spinner("JAPAN AI が解析中..."):
        try:
            # 画像をBase64に変換
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # APIリクエストの作成
            # artifactIdsを空にすることで、データセット検索ではなく「添付画像」の解析を強制します
            payload = {
                "model": API_MODEL_TITLE,
                "prompt": "添付した画像の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力してください。",
                "stream": False,
                "temperature": 0.0,
                "artifactIds": [], # ここを空にするのがポイントです
                "images": [img_str]
            }
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            response = requests.post(API_URL, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                result_json = response.json()
                title = result_json.get("chatMessage", "").strip()
                
                # 不要な接頭辞を除去
                title = title.replace("出力タイトル：", "").replace("タイトル：", "").replace("タイトル:", "")
                
                if "見つかりませんでした" in title or not title:
                    st.warning("AIが画像を認識できませんでした。光量や角度を変えてみてください。")
                else:
                    st.success(f"🏷️ タイトル: {title}")
            else:
                st.error(f"APIエラー: {response.status_code}")
                
        except Exception as e:
            st.error(f"解析エラー: {str(e)}")

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
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                output.innerText = formattedAddress || "住所が見つかりませんでした";
            } catch (err) { output.innerText = "住所の特定に失敗しました。"; }
        },
        (err) => { output.innerText = "エラー: 位置情報の許可が必要です。"; },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
