import streamlit as st

img_file = st.camera_input("写真を撮る")

if img_file:
    # ダウンロードボタンを表示
    st.download_button(
        label="スマホに保存する",
        data=img_file,
        file_name="captured_image.png",
        mime="image/png"
    )
