import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io

# --- Gemini API 設定 ---
API_KEY = "AIzaSyAC6W0cwPmw3VrpxqXoiKZEv4CpIYUHME0"
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image
import io

# --- Gemini API 設定 ---
API_KEY = "AIzaSyAC6W0cwPmw3VrpxqXoiKZEv4CpIYUHME0"
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="写真解析", layout="centered")

st.title("写真解析・撮影")

# カメラ入力
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    with st.spinner("Geminiがタイトルを生成中..."):
        try:
            # 利用可能なモデルを確認して自動選択するロジック
            # (1.5 Flashを最優先し、ダメなら1.0 Pro Visionを使う)
            model_name = 'gemini-1.5-flash'
            try:
                model = genai.GenerativeModel(model_name)
                # 起動確認のためのダミー処理
                response = model.generate_content(["Ready", img])
            except:
                model_name = 'gemini-pro-vision'
                model = genai.GenerativeModel(model_name)

            # 実際のタイトル生成
            prompt = "この写真の内容を分析し、20文字以内の日本語で短いタイトルを付けてください。結果のみを出力してください。"
            response = model.generate_content([prompt, img])
            
            if response.text:
                title = response.text.strip()
                st.success(f"🏷️ タイトル: {title}")
            else:
                st.warning("内容を読み取れませんでした。")
                
        except Exception as e:
            st.error(f"解析エラーが発生しました。")
            st.code(f"Error Detail: {str(e)}")
            st.info("💡 解消法: requirements.txt に 'google-generativeai>=0.5.0' と書き、アプリをReboot（再起動）してください。")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 住所取得ロジック（都道府県抜き）
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const addr = data.address;
                let formattedAddress = "";
                if (addr.city) formattedAddress += addr.city;
                if (addr.suburb) formattedAddress += addr.suburb;
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) formattedAddress += addr.city_district;
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                output.innerText = formattedAddress || "住所が見つかりませんでした";
            } catch (err) { output.innerText = "住所特定失敗"; }
        },
        (err) => { output.innerText = "位置情報エラー"; },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
img_file = st.camera_input("写真を撮る")

if img_file:
    # 画像を表示
    img = Image.open(img_file)
    st.image(img, caption="撮影した写真")

    # --- Gemini 解析セクション ---
    with st.spinner("Geminiがタイトルを生成中..."):
        try:
            # 1. まず最新の Flash モデルを試行
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(["この写真に20文字以内の日本語タイトルを付けてください。結果のみ出力してください。", img])
            except Exception:
                # 2. 失敗した場合、旧来の Vision モデルを試行（互換性のため）
                model = genai.GenerativeModel('gemini-pro-vision')
                response = model.generate_content(["この写真に20文字以内の日本語タイトルを付けてください。結果のみ出力してください。", img])
            
            # テキストの抽出
            if response and response.text:
                title = response.text.strip()
                st.success(f"🏷️ タイトル: {title}")
            else:
                st.warning("タイトルを生成できませんでした。もう一度撮影してください。")
                
        except Exception as e:
            st.error(f"Gemini解析エラー: {str(e)}")
            st.info("💡 依然としてエラーが出る場合は、requirements.txt に google-generativeai==0.5.0 以上が記載されているか確認してください。")

    st.write("---")
    st.subheader("📍 撮影場所")

    # 住所取得ロジック（都道府県抜き）
    address_script = """
    <div id="address-out" style="font-weight:bold; color:#1f77b4; padding:10px; background-color:#f0f2f6; border-radius:5px; font-size:14px;">
        位置情報を取得中...
    </div>
    <script>
    const output = document.getElementById('address-out');
    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`, {
                    headers: { 'Accept-Language': 'ja' }
                });
                const data = await response.json();
                const addr = data.address;
                let formattedAddress = "";
                
                if (addr.city) formattedAddress += addr.city;
                if (addr.suburb) formattedAddress += addr.suburb;
                if (addr.city_district && !formattedAddress.includes(addr.city_district)) {
                    formattedAddress += addr.city_district;
                }
                if (addr.neighbourhood) formattedAddress += addr.neighbourhood;
                
                output.innerText = formattedAddress || "住所が見つかりませんでした";
            } catch (err) {
                output.innerText = "住所の特定に失敗しました。";
            }
        },
        (err) => {
            output.innerText = "エラー: 位置情報の許可が必要です。";
        },
        { enableHighAccuracy: true }
    );
    </script>
    """
    components.html(address_script, height=80)

    st.info("💡 保存するには、上の写真を長押しして「'写真'に追加」を選択してください。")
    
    if st.button("撮り直す"):
        st.rerun()
