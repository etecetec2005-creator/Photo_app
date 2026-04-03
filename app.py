import streamlit as st
from PIL import Image
import io

# ページ設定（iPhone SEの画面サイズに配慮）
st.set_page_config(page_title="高画質カメラ保存", layout="centered")

st.title("📷 高画質写真撮影")

# 改善案2: file_uploaderを使用して標準カメラを呼び出す
# iPhoneではこれをクリックすると「写真を撮る」という選択肢が出ます
img_file = st.file_uploader(
    "タップしてカメラを起動", 
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False
)

if img_file:
    # プレビュー表示
    image = Image.open(img_file)
    st.image(image, caption="撮影された写真（プレビュー）", use_container_width=True)
    
    # ------------------------------------------------
    # 保存処理（高画質を維持してバイトデータ化）
    # ------------------------------------------------
    buf = io.BytesIO()
    # JPEG形式で品質100（無圧縮に近い状態）で書き出し
    image.save(buf, format="JPEG", quality=100, subsampling=0)
    byte_im = buf.getvalue()

    # 保存ボタン（iPhoneでの「戻れない」問題を回避するための案内付き）
    st.info("💡 iPhone本体に保存する場合：下のボタンを押した後、表示された画像を『長押し』して『\"写真\"に追加』を選択してください。")
    
    st.download_button(
        label="📥 写真を保存する処理へ進む",
        data=byte_im,
        file_name="high_quality_photo.jpg",
        mime="image/jpeg"
    )

    # 撮り直しボタン
    if st.button("リセット（別の写真を撮る）"):
        st.rerun()

else:
    st.write("上のボタンをタップして、カメラで撮影してください。")
    st.caption("※標準カメラアプリが起動するため、文字や細部まで鮮明に写ります。")
