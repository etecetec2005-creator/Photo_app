import streamlit as st
import streamlit.components.v1 as components
import requests

st.title("写真撮影 & 住所取得")

# 1. 写真撮影
img_file = st.camera_input("写真を撮る")

if img_file:
    st.image(img_file, caption="撮影した写真")
    
    st.write("---")
    st.subheader("📍 撮影場所の情報")

    # JavaScriptで位置情報を取得し、そのまま住所に変換して表示する仕組み
    # Nominatim API（無料の住所変換サービス）を使用します
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; border:1px solid #ddd; border-radius:5px;">
        位置情報を取得中...
    </div>

    <script>
    const output = document.getElementById('address-out');

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            
            try {
                // 座標を住所に変換するAPIを呼び出し
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const address = data.display_name;
                
                output.innerText = "現在地： " + address;
            } catch (err) {
                output.innerText = "住所の特定に失敗しました。";
            }
        },
        (err) => {
            output.innerText = "エラー: 位置情報の取得を許可してください。";
        },
        { enableHighAccuracy: true }
    );
    </script>
    """
    
    # 住所表示部分を実行
    components.html(address_script, height=150)

    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
