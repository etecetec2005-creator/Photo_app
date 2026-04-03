import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="写真撮影", layout="centered")

st.title("写真撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    st.image(img_file, caption="撮影した写真")
    
    st.write("---")
    st.subheader("📍 撮影場所")

    # 都道府県名を除外した住所取得ロジック
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>

    <script>
    const output = document.getElementById('address-out');

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const addr = data.address;
                
                let formattedAddress = "";
                
                // 都道府県(province)はスキップし、市区町村以降を結合
                if (addr.city) formattedAddress += addr.city;         // 大阪市
                if (addr.suburb) formattedAddress += addr.suburb;     // 淀川区
                
                if (addr.city_district) {
                    if (!formattedAddress.includes(addr.city_district)) {
                        formattedAddress += addr.city_district;
                    }
                }
                
                if (addr.neighbourhood) {
                    formattedAddress += addr.neighbourhood;           // 宮原一丁目
                } else if (addr.suburb && !formattedAddress.includes(addr.suburb)) {
                    // neighbourhoodがない場合の補完
                    formattedAddress += addr.suburb;
                }

                // 結合結果が空の場合のフォールバック
                if (!formattedAddress) {
                    // 全体文字列から都道府県部分をカットする簡易処理
                    formattedAddress = data.display_name.split(',')[0];
                }

                output.innerText = formattedAddress;
                
            } catch (err) {
                output.innerText = "住所の特定に失敗しました。";
            }
        },
        (err) => {
            output.innerText = "エラー: 位置情報の取得を許可してください。";
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
    </script>
    """
    
    # 表示エリアの実行
    components.html(address_script, height=80)

    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
