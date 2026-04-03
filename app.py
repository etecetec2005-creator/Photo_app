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
ARTIFACT_ID = "ba011f66-7e30-49ee-b7a0-2417a7ee26bf"

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- JAPAN AI 解析セクション ---
    with st.spinner("JAPAN AI がタイトルを生成中..."):
        try:
            # 画像をBase64に変換
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # APIリクエストの作成
            payload = {
                "model": API_MODEL_TITLE,
                "prompt": "この写真の内容を一言で表す短いタイトル（20文字以内）を付けてください。結果のみを出力し、説明は不要です。",
                "stream": False,
                "temperature": 0.0,
                "artifactIds": [ARTIFACT_ID],
                "images": [img_str]
            }
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            # 実行
            response = requests.post(API_URL, json=payload, headers=headers)
            
            # 【修正点】200(OK) または 201(Created) の場合に処理を続行
            if response.status_code in [200, 201]:
                result_json = response.json()
                # chatMessage フィールドから取得
                title = result_json.get("chatMessage", "").strip()
                
                # 接頭辞の除去
                title = title.replace("出力タイトル：", "").replace("タイトル：", "").replace("タイトル:", "")
                
                if title:
                    st.success(f"🏷️ タイトル: {title}")
                else:
                    st.warning("タイトルを取得できましたが、内容が空でした。")
            else:
                st.error(f"APIエラー: {response.status_code}\n{response.text}")
                
        except Exception as e:
            st.error(f"解析中にエラーが発生しました: {str(e)}")

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
        (err) => { output.innerText = "エラー: 位置情報の取得を許可してください。"; },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
