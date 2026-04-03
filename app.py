import streamlit as st
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="写真撮影", layout="centered")

st.title("写真撮影")

# 位置情報を取得するためのJavaScript
# ブラウザの機能を使用して緯度・経度を取得します
location_script = """
<script>
navigator.geolocation.getCurrentPosition(
    (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        // Streamlit側に値を送るためのカスタムイベント（隠し要素に値をセット）
        window.parent.document.dispatchEvent(new CustomEvent("LOCATION_UPDATED", {detail: {lat: lat, lon: lon}}));
    },
    (error) => {
        console.error("位置情報の取得に失敗しました", error);
    }
);
</script>
"""

# JavaScriptを実行
components.html(location_script, height=0)

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    st.image(img_file, caption="撮影した写真")
    
    # 住所を表示するためのエリア
    st.write("---")
    st.subheader("📍 撮影場所の情報")
    
    # 注意：ブラウザからの座標取得には数秒かかる場合があります
    # 簡易的に、撮影時に「場所を確認する」ボタンを表示する構成にします
    if st.button("現在地の住所を取得"):
        st.warning("位置情報を取得中...（ブラウザの許可ダイアログが出たら承認してください）")
        # 実際の実装では、API経由やExifからの取得が安定しますが、
        # まずはカメラ機能とUIの維持を優先しています。
        st.write("※現在、Webブラウザの制限によりカメラと位置情報の同時取得にはHTTPS環境が必要です。")

    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
