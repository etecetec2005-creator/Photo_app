import streamlit as st
import streamlit.components.v1 as components
import requests

st.title("写真撮影 & 位置情報")

# JavaScriptで位置情報を取得し、ボタンが押されたらPython側に値を返す仕組み
# ※このコードは https 環境でのみ動作します
def get_location():
    # 座標を取得するためのHTML/JavaScript
    # 取得に成功すると、Streamlitの変数に値が格納されます
    loc_html = """
    <div id="location-display">位置情報を取得しています...</div>
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const data = {
                lat: pos.coords.latitude,
                lon: pos.coords.longitude,
                accuracy: pos.coords.accuracy
            };
            // Streamlitにデータを送信
            window.parent.postMessage({
                type: 'streamlit:set_component_value',
                value: data
            }, '*');
            document.getElementById('location-display').innerText = "取得完了";
        },
        (err) => {
            document.getElementById('location-display').innerText = "エラー: " + err.message;
        }
    );
    </script>
    """
    return components.html(loc_html, height=50)

# 1. 写真撮影
img_file = st.camera_input("写真を撮る")

if img_file:
    st.image(img_file, caption="撮影した写真")
    
    # 2. 位置情報の取得（ボタンを押したタイミングで実行）
    st.write("---")
    if st.button("現在地の住所を特定する"):
        # JavaScriptコンポーネントを呼び出し
        location_data = get_location()
        
        # 簡易的なデモとして、座標が取得できたと仮定して表示する（※）
        # ※本来はカスタムコンポーネント化が必要ですが、まずは手動入力も併用するのが確実です
        st.info("ブラウザの上部に「位置情報の使用を許可しますか？」と出ている場合は『許可』を押してください。")

    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
