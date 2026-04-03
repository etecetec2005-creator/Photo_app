import streamlit as st
from streamlit_components_dot_com import html_component # 代替案として標準のst.components.v1を使用
import streamlit.components.v1 as components
import requests

st.title("写真撮影")

# 位置情報を取得するためのJavaScript
location_script = """
<script>
navigator.geolocation.getCurrentPosition(
    (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        window.parent.postMessage({
            type: 'streamlit:set_component_value',
            lat: lat,
            lon: lon
        }, '*');
    },
    (error) => {
        console.error("位置情報の取得に失敗しました", error);
    }
);
</script>
"""

# 位置情報受け取り用のコンポーネント（非表示）
location_data = components.html(location_script, height=0)

# 緯度経度から住所を取得する関数
def get_address(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        response = requests.get(url, headers={'User-Agent': 'StreamlitApp'})
        data = response.json()
        return data.get("display_name", "住所が見つかりませんでした")
    except Exception:
        return "住所取得エラー"

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    st.image(img_file, caption="撮影した写真")
    
    # 座標が取得できているか確認（ブラウザの許可が必要）
    # 注：実際の運用では、JavaScriptからのデータ受け取りにカスタムコンポーネントの知識が必要ですが、
    # 簡易的に住所入力欄や「場所を特定」ボタンを設けるのが確実です。
    
    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    # 撮り直すボタン
    if st.button("撮り直す"):
        st.rerun()

# 補足説明
st.write("---")
st.caption("※位置情報の表示には、ブラウザで位置情報の使用を許可する必要があります。")
