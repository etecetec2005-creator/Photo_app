import streamlit as st

st.title("写真撮影")

img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示する
    st.image(img_file, caption="撮影した写真")
    
    # メッセージで保存方法を案内する
    st.info("💡 iPhoneに保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    # 撮り直したい場合のために再実行ボタンを配置（任意）
    if st.button("撮り直す"):
        st.rerun()
