import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(page_title="写真解析・保存", layout="centered")
st.title("📸 写真解析・確定保存")

img_file = st.camera_input("写真を撮る")

if img_file:
    raw_img = Image.open(img_file)
    
    # 1. AI解析と住所取得を並行して行う
    with st.spinner("解析・住所取得中..."):
        # AIタイトル生成
        ai_title = "名称未設定"
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
            model = genai.GenerativeModel(target_model)
            response = model.generate_content(["この写真に短い日本語タイトルを付けて。結果のみ。", raw_img])
            if response.text:
                ai_title = response.text.strip().replace("/", "-")
        except:
            pass

        # 住所取得 (Python側で実行して確実に取得)
        address = "不明な場所"
        try:
            res = requests.get("http://ip-api.com/json/?lang=ja", timeout=5).json()
            if res.get("status") == "success":
                address = f"{res.get('city', '')}{res.get('district', '')}"
        except:
            pass

    # 2. 【文字化け対策】画像の下に白帯を作って、そこに住所とタイトルを書き込む
    def draw_info_on_img(img, addr, title):
        w, h = img.size
        # 下部に15%ほどの余白を作成
        padding = int(h * 0.15)
        new_img = Image.new("RGB", (w, h + padding), (255, 255, 255))
        new_img.paste(img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        # フォントが指定できない場合でも、大きなサイズで描画できるようデフォルトを使用
        try:
            # Streamlit Cloud (Linux) の標準日本語フォント
            font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", int(padding * 0.3))
        except:
            font = ImageFont.load_default()
            
        draw.text((20, h + 10), f"📍 {addr}", fill=(0, 0, 0), font=font)
        draw.text((20, h + 10 + int(padding * 0.4)), f"🏷️ {title}", fill=(0, 0, 0), font=font)
        return new_img

    final_img = draw_info_on_img(raw_img, address, ai_title)
    
    # 画面に「文字入り画像」を表示
    st.image(final_img, caption="この内容で保存します")

    # 3. 保存ボタン (一発ダウンロード)
    filename = f"{address}_{ai_title}.jpg"
    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=90)
    
    st.download_button(
        label=f"📥 {filename} を保存",
        data=buf.getvalue(),
        file_name=filename,
        mime="image/jpeg",
        use_container_width=True
    )
    
    st.info("※iPhoneの場合、保存後に『ファイル』アプリのダウンロードフォルダに入ります。")

    if st.button("撮り直す"):
        st.rerun()
