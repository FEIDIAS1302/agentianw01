import streamlit as st
import google.generativeai as genai
import json
import re
import zipfile
import io
import datetime
import requests
import webbrowser
import os
from PIL import Image, ImageOps
from PyPDF2 import PdfReader
from pptx import Presentation

# --- デザイン設定  ---
st.set_page_config(page_title="AGENTIA for NUWORKS", layout="wide", page_icon="◾️")

# CSS注入: ミニマル・モノトーン・高品質なUI
st.markdown("""
<style>
    /* 全体のフォントと背景 */
    .stApp {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        background-color: #ffffff;
        color: #1a1a1a;
    }
    /* ヘッダー周り */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.05em !important;
        color: #000000 !important;
    }
    h1 { font-size: 3rem !important; margin-bottom: 0.5rem !important; }
    
    /* 入力フォームのスタイル */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #e0e0e0 !important;
        padding: 0.5rem !important;
    }
    
    /* ボタンのスタイル (黒背景・白文字) */
    .stButton button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 30px !important;
        font-weight: bold !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #333333 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }

    /* 画像の角丸 */
    img {
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        /* ↓ この1行を追加します (薄いグレー) */
        background-color: #f5f5f5; 
        /* 画像が枠内に収まるように調整 */
        object-fit: contain;
    }
    
    /* ディバイダー */
    hr {
        border-color: #f0f0f0;
        margin: 3rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 設定 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- データ定義 (プレースホルダー) ---
# ※本番では assets/bg_01.jpg などのパスを指定してください
BACKGROUNDS = {
    "bg_01": {"name": "Blue abstarct", "url": "assets/bg_01.jpg"},
    "bg_02": {"name": "White marble", "url": "assets/bg_02.jpg"},
    "bg_03": {"name": "Rooms", "url": "assets/bg_03.jpg"},
    "bg_04": {"name": "Tech", "url": "assets/bg_04.jpg"},
}

# アバター画像 (縦長 9:16 の透過PNGを想定)
AVATARS = {
    # サイズを 300x400 から 270x480 に変更
    # ※ここには実際の透過PNGのパスを指定することになります
    "avatar_a": {"name": "Avatar01", "url": "assets/avat_01.png"},
    "avatar_b": {"name": "Avatar02", "url": "assets/avat_02.png"},
    "avatar_c": {"name": "Avatar03", "url": "assets/avat_03.png"},
    "avatar_d": {"name": "Avatar04", "url": "assets/avat_04.png"},
}

BGMS = {
    "bgm_01": {
        "name": "Trust & Corporate", 
        "desc": "信頼感のある明るいサウンド",
        # ↓ これを追加 (実際のファイルパス または URL)
        "path": "assets/bgm1.mp3" 
    },
    "bgm_02": {
        "name": "Innovation Tech", 
        "desc": "先進的なデジタルビート",
        "path": "assets/bgm2.mp3"
    },
    "bgm_03": {
        "name": "Morning", 
        "desc": "落ち着いた楽曲",
        "path": "assets/bgm3.mp3"
    },
    "bgm_04": {
        "name": "Future", 
        "desc": "エネルギッシュなBGM",
        "path": "assets/bgm4.mp3"
    },
}

# --- ユーティリティ関数 ---

def load_image_from_url_or_path(path_or_url):
    """URLまたはローカルパスからPIL画像を開く"""
    try:
        if path_or_url.startswith("http"):
            response = requests.get(path_or_url, stream=True)
            return Image.open(response.raw).convert("RGBA")
        else:
            return Image.open(path_or_url).convert("RGBA")
    except:
        return Image.new("RGBA", (1920, 1080), (200, 200, 200, 255))

def create_preview(bg_key, avatar_key, logo_upload):
    """
    PILを使って高速にプレビュー画像を合成する
    """
    # 1. 背景の読み込み & リサイズ
    bg_img = load_image_from_url_or_path(BACKGROUNDS[bg_key]['url'])
    bg_img = bg_img.resize((1920, 1080))

    # 2. アバターの読み込み (簡易表示)
    # ※実際はここで透過PNGのアバター立ち絵を使います
    avatar_img = load_image_from_url_or_path(AVATARS[avatar_key]['url'])
    # アバターを画面下中央に配置する計算
    # 高さを900pxくらいに調整
    avatar_ratio = avatar_img.width / avatar_img.height
    new_h = 900
    new_w = int(new_h * avatar_ratio)
    avatar_img = avatar_img.resize((new_w, new_h))
    
    # 貼り付け位置 (中央, 下揃え)
    x_pos = (1920 - new_w) // 2
    y_pos = 1080 - new_h
    bg_img.paste(avatar_img, (x_pos, y_pos), avatar_img) # 3つ目の引数はマスク(透過用)

    # 3. ロゴの読み込み
    if logo_upload:
        logo_img = Image.open(logo_upload).convert("RGBA")
        # ロゴをリサイズ (高さ80px)
        l_ratio = logo_img.width / logo_img.height
        l_h = 80
        l_w = int(l_h * l_ratio)
        logo_img = logo_img.resize((l_w, l_h))
        
        # 左上に配置
        bg_img.paste(logo_img, (60, 60), logo_img)

    return bg_img

def extract_text(file):
    text = ""
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages: text += page.extract_text()
        elif file.name.endswith(".pptx"):
            prs = Presentation(file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"): text += shape.text + "\n"
    except: pass
    return text

def generate_script(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"会社説明動画の台本を作成してください。1500文字程度。内容は以下の通り:\n{text[:30000]}"
    return model.generate_content(prompt).text

# --- メインレイアウト ---

st.title("NuWorks Studio.")
st.markdown("Create your corporate video in minutes.")

# --- 左カラム: 入力 / 右カラム: プレビュー ---
col_input, col_preview = st.columns([1, 1.2], gap="large")

with col_input:
    st.markdown("### 1. Basic Info")
    project_id = st.text_input("Project ID", placeholder="NW10001")
    company_name = st.text_input("Company Name", placeholder="NuWorks Inc.")
    
    st.markdown("### 2. Assets")
    logo_file = st.file_uploader("Company Logo (PNG)", type=["png"])

    st.markdown("### 3. Visual Style")
    
    # --- 背景選択 (サムネイル付き) ---
    st.caption("Select Background")
    
    # 辞書のキーをリスト化
    bg_keys = list(BACKGROUNDS.keys())
    
    # 4列のカラムを作成
    bg_cols = st.columns(4)
    
    # ループで画像を正方形に加工して表示
    for i, key in enumerate(bg_keys):
        with bg_cols[i]:
            # 画像を読み込む
            img = load_image_from_url_or_path(BACKGROUNDS[key]['url'])
            
            # 【重要】正方形にセンタークロップ（真ん中を切り抜き）
            # 短い方の辺に合わせて正方形を作る計算
            min_side = min(img.width, img.height)
            # ImageOps.fit は自動で「いい感じ」に真ん中を切り抜いてくれます
            square_img = ImageOps.fit(img, (min_side, min_side), centering=(0.5, 0.5))
            
            # 表示
            st.image(square_img, use_column_width=True)
            st.caption(BACKGROUNDS[key]['name'])

    # ラジオボタンで選択させる（画像の下に配置）
    bg_choice = st.radio(
        "Choose Background", 
        bg_keys, 
        format_func=lambda x: BACKGROUNDS[x]['name'], 
        horizontal=True,
        label_visibility="collapsed" # ラベルを隠してすっきりさせる
    )

    # アバター選択 (ビジュアルグリッド)
    st.caption("Select Avatar")
    
    # 2列x2行で画像を表示し、下のラジオボタンで選ばせるUI
    # (Streamlit標準機能で最も綺麗に見せる方法)
    av_keys = list(AVATARS.keys())
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.image(AVATARS['avatar_a']['url']); st.caption("A")
    with c2: st.image(AVATARS['avatar_b']['url']); st.caption("B")
    with c3: st.image(AVATARS['avatar_c']['url']); st.caption("C")
    with c4: st.image(AVATARS['avatar_d']['url']); st.caption("D")
    
    avatar_choice = st.radio("Choose Model", av_keys, format_func=lambda x: AVATARS[x]['name'], horizontal=True)

    st.markdown("### 4. Audio")
    
    # BGM選択ボックス
    bgm_choice = st.selectbox(
        "Background Music", 
        list(BGMS.keys()), 
        format_func=lambda x: BGMS[x]['name']
    )
    
    # --- 追加: 選択されたBGMの説明と試聴プレイヤー ---
    selected_bgm = BGMS[bgm_choice]
    st.caption(f"♪ {selected_bgm['desc']}") # 説明文を表示
    
    # 音楽ファイルのパスを取得
    audio_path = selected_bgm['path']
    
    # ファイルが存在するか(またはURLか)確認してプレイヤーを表示
    try:
        # ローカルファイルの場合の処理
        if not audio_path.startswith("http"):
            st.audio(audio_path, format="audio/mp3")
        else:
            # URLの場合の処理
            st.audio(audio_path, format="audio/mp3")
    except Exception:
        st.warning("⚠️ 音声ファイルが見つかりません (assetsフォルダを確認してください)")
    
    st.markdown("### 5. Document")
    doc_file = st.file_uploader("Upload Company Profile (PDF/PPTX)", type=["pdf", "pptx"])
    
    if st.button("Generate Script & Package", type="primary"):
        if doc_file and company_name and project_id:
            with st.spinner("Analyzing document..."):
                txt = extract_text(doc_file)
                script = generate_script(txt)
                st.session_state['result'] = script
                st.success("Completed.")
        else:
            st.error("Please fill all required fields.")

# --- 右カラム: リアルタイムプレビュー ---
with col_preview:
    st.markdown("### Preview")
    
    # コンテナを作ってカード風にする
    with st.container():
        # プレビュー画像の生成
        preview_img = create_preview(bg_choice, avatar_choice, logo_file)
        
        # 表示
        st.image(preview_img, caption="Real-time Composite Preview", use_column_width=True)
        
        # 選択情報のサマリー
        st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:1.5rem; border-radius:10px; border:1px solid #eee;">
            <p style="margin:0; font-size:0.9rem; color:#888;">SELECTED CONFIGURATION</p>
            <h4 style="margin:0.5rem 0;">{BACKGROUNDS[bg_choice]['name']} / {AVATARS[avatar_choice]['name']}</h4>
            <p style="margin:0; font-size:0.9rem; color:#666;">🎵 BGM: {BGMS[bgm_choice]['name']}</p>
        </div>
        """, unsafe_allow_html=True)

    # 台本生成結果の表示
    if 'result' in st.session_state:
        st.markdown("### Generated Script")
        final_script = st.text_area("", st.session_state['result'], height=300)
        
       # --- ZIP生成関数 ---
def create_order_zip(order_data, logo_file, doc_file):
    """メモリ上でZIPファイルを作成する関数"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. JSONファイルを書き込み
        json_str = json.dumps(order_data, indent=4, ensure_ascii=False)
        zf.writestr("order.json", json_str)
        
        # 2. ロゴ画像を書き込み
        if logo_file:
            logo_file.seek(0)
            # 拡張子を維持
            ext = logo_file.name.split('.')[-1]
            zf.writestr(f"logo.{ext}", logo_file.read())
            
        # 3. 資料ファイルを書き込み
        if doc_file:
            doc_file.seek(0)
            zf.writestr(doc_file.name, doc_file.read())
            
    return zip_buffer.getvalue()

# --- ボタン部分の実装 ---

    # (Generateボタンはそのまま)
    if st.button("Generate Script & Create Package", type="primary"):
        if doc_file and company_name and project_id:
            with st.spinner("Analyzing & Packaging..."):
                
                # 1. 台本生成
                txt = extract_text(doc_file)
                script = generate_script(txt)
                st.session_state['result'] = script # プレビュー表示用
                
                # 2. データ作成
                timestamp = datetime.datetime.now().strftime("%Y%m%d")
                order_data = {
                    "project_id": project_id,
                    "company_name": company_name,
                    "date": timestamp,
                    "background_id": bg_choice,
                    "avatar_id": avatar_choice,
                    "bgm_id": bgm_choice,
                    "script": script
                }
                
                # 3. ZIPファイルのバイナリデータを作成
                zip_data = create_order_zip(order_data, logo_file, doc_file)
                
                # ZIPをローカルに一時保存
                zip_filename = f"{project_id}_{company_name}_{timestamp}.zip"
                with open(zip_filename, "wb") as f:
                    f.write(zip_data)
                
                st.success("📦 ZIP Created!")
                
                # --- ここが魔法のコード ---
                if st.button("🚀 Dropboxへアップロード (画面を開く)"):
                    # 1. あなたのDropboxファイルリクエストのURL
                    dropbox_url = "https://www.dropbox.com/request/hxd6z70hxhV1fTG4rmVw"
                    
                    # 2. ブラウザでDropboxを開く
                    webbrowser.open(dropbox_url)
                    
                    # 3. エクスプローラーでZIPがある場所を開く (Windows用)
                    # ファイルを選択した状態でフォルダを開きます
                    subprocess.Popen(f'explorer /select,"{os.path.abspath(zip_filename)}"')