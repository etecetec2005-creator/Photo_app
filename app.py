from PIL import Image
import streamlit as st
import io

img_file = st.camera_input("写真を撮る")

if img_file:
    # 1. 画像データとして読み込む
    image = Image.open(img_file)
    
    # 2. 最高画質でバイトデータに変換し直す (PNGなら無劣化、JPEGならquality=100)
    buf = io.BytesIO()
    image.save(buf, format="PNG")  # 無劣化保存ならPNGを推奨
    byte_im = buf.getvalue()

    st.image(image, caption="プレビュー")

    # ダウンロードボタンに最高画質のデータを渡す
    st.download_button(
        label="最高画質で保存",
        data=byte_im,
        file_name="high_quality_photo.png",
        mime="image/png"
    )
